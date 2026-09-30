"""Receive GitHub events and deliver notifications through AstrBot."""

import asyncio
import json
import time
from collections import OrderedDict
from contextlib import suppress

from aiohttp import web
from astrbot.api import logger
from astrbot.api.event import MessageChain
from astrbot.api.message_components import Plain
from astrbot.api.star import Context
from astrbot.core.config.default import VERSION
from packaging.version import Version

from ..handlers.issues_handler import handle_issues_event
from ..handlers.pull_request_handler import handle_pull_request_event
from ..handlers.push_handler import handle_push_event
from ..handlers.star_handler import handle_star_event
from ..services.llm_service import generate_message
from ..utils.rate_limiter import RateLimiter
from ..utils.verify_signature import verify_signature
from .config import PluginConfig


class GitHubWebhookPlugin:
    """Keep slow model and platform requests outside the HTTP response path."""

    def __init__(self, context: Context, config):
        self.context = context
        self.cfg = PluginConfig(config)
        self.app = web.Application()
        self.app.router.add_post("/webhook", self.handle_webhook)
        self.app.cleanup_ctx.append(self._worker_lifecycle)
        self.runner = None
        self.site = None
        self.queue = asyncio.Queue(maxsize=100)
        self.pending_deliveries = set()
        self.completed_deliveries = OrderedDict()
        self.accepting = False
        self.shutdown_timeout = 10
        self.supports_qq_markdown = Version(VERSION) >= Version("4.28.0")
        self.rate_limiter = (
            RateLimiter(self.cfg.rate_limit) if self.cfg.rate_limit else None
        )

    async def _worker_lifecycle(self, app):
        worker = asyncio.create_task(self._process_queue())
        self.accepting = True
        try:
            yield
        finally:
            self.accepting = False
            try:
                await asyncio.wait_for(self.queue.join(), self.shutdown_timeout)
            except asyncio.TimeoutError:
                logger.warning(
                    "GitHub Webhook: shutdown timed out; unfinished notifications "
                    "must be redelivered from GitHub"
                )
            finally:
                worker.cancel()
                with suppress(asyncio.CancelledError):
                    await worker
                while not self.queue.empty():
                    delivery_id, _, _, _ = self.queue.get_nowait()
                    logger.warning(
                        f"GitHub Webhook: unsent on shutdown, id={delivery_id or '(none)'}"
                    )
                    self.pending_deliveries.discard(delivery_id)
                    self.queue.task_done()

    async def start_server(self):
        if self.runner is not None:
            return
        self.runner = web.AppRunner(self.app)
        try:
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "0.0.0.0", self.cfg.port)
            await self.site.start()
        except Exception:
            await self.runner.cleanup()
            self.runner = None
            self.site = None
            raise
        logger.info(f"GitHub Webhook: listening on port {self.cfg.port}")

    async def handle_webhook(self, request: web.Request):
        payload = await request.read()
        signature = request.headers.get("X-Hub-Signature-256", "")
        if self.cfg.webhook_secret and not verify_signature(
            payload, signature, self.cfg.webhook_secret
        ):
            return web.Response(status=401, text="Invalid or missing signature")
        try:
            data = json.loads(payload)
        except (ValueError, UnicodeDecodeError):
            return web.Response(status=400, text="Invalid JSON")
        if not isinstance(data, dict):
            return web.Response(status=400, text="Expected a JSON object")

        event_type = request.headers.get("X-GitHub-Event", "unknown")
        if event_type == "ping":
            return web.Response(text="Pong")
        handlers = {
            "push": handle_push_event,
            "issues": handle_issues_event,
            "pull_request": handle_pull_request_event,
            "star": handle_star_event,
        }
        if event_type not in handlers:
            return web.Response(status=204)
        if not self.accepting or not self.cfg.target_umo:
            return web.Response(status=503, text="Receiver is not ready")

        platform_id = self.cfg.target_umo.split(":", 1)[0]
        platform = self.context.get_platform_inst(platform_id)
        if platform is None:
            return web.Response(status=503, text="Target platform is unavailable")
        markdown = self.cfg.push_mode != "原生文本" and platform.meta().name in {
            "qq_official",
            "qq_official_webhook",
        }
        if markdown and not self.supports_qq_markdown:
            return web.Response(
                status=503,
                text="QQ proactive Markdown requires AstrBot >= 4.28.0; "
                "upgrade AstrBot or select native text mode",
            )
        try:
            message = await handlers[event_type](data, self.context, markdown=markdown)
        except (KeyError, TypeError, ValueError, AttributeError):
            return web.Response(status=400, text="Invalid event payload")
        if not message:
            return web.Response(status=204)

        delivery_id = request.headers.get("X-GitHub-Delivery", "")
        now = time.monotonic()
        while self.completed_deliveries:
            oldest_id, completed_at = next(iter(self.completed_deliveries.items()))
            if now - completed_at < 3600:
                break
            del self.completed_deliveries[oldest_id]
        if delivery_id and (
            delivery_id in self.pending_deliveries
            or delivery_id in self.completed_deliveries
        ):
            return web.Response(text="Already accepted")
        if self.queue.full():
            return web.Response(status=503, text="Notification queue is full")
        if self.rate_limiter:
            allowed, retry_after = await self.rate_limiter.is_allowed()
            if not allowed:
                return web.Response(
                    status=429,
                    text="Rate limit exceeded",
                    headers={"Retry-After": str(retry_after)},
                )
        try:
            self.queue.put_nowait((delivery_id, event_type, message, markdown))
        except asyncio.QueueFull:
            return web.Response(status=503, text="Notification queue is full")
        if delivery_id:
            self.pending_deliveries.add(delivery_id)
        return web.Response(status=202, text="Accepted for background delivery")

    async def _process_queue(self):
        while True:
            delivery_id, event_type, message, markdown = await self.queue.get()
            try:
                if self.cfg.push_mode == "LLM 改写":
                    try:
                        message = await asyncio.wait_for(
                            generate_message(self, message, markdown),
                            timeout=self.cfg.agent_timeout,
                        )
                    except asyncio.TimeoutError:
                        if not self.cfg.llm_timeout_fallback_md:
                            raise
                        logger.warning(
                            "GitHub Webhook: LLM timed out; sending the event template"
                        )
                await self.send_message(message, markdown)
                if delivery_id:
                    self.completed_deliveries[delivery_id] = time.monotonic()
                    while len(self.completed_deliveries) > 1024:
                        self.completed_deliveries.popitem(last=False)
                logger.info(
                    f"GitHub Webhook: delivered {event_type}, id={delivery_id or '(none)'}"
                )
            except asyncio.CancelledError:
                logger.warning(
                    f"GitHub Webhook: interrupted delivery, id={delivery_id or '(none)'}"
                )
                raise
            except Exception:
                logger.exception(
                    f"GitHub Webhook: delivery failed, id={delivery_id or '(none)'}. "
                    "Redeliver this event from GitHub after fixing the error."
                )
            finally:
                self.pending_deliveries.discard(delivery_id)
                self.queue.task_done()

    async def send_message(self, message: str, markdown: bool = False):
        if markdown and self.cfg.qq_mention_openid:
            message = (
                f'<qqbot-at-user id="{self.cfg.qq_mention_openid}" />\n\n{message}'
            )
        chain = MessageChain([Plain(message)])
        if hasattr(chain, "use_markdown"):
            chain.use_markdown(markdown)
        result = await asyncio.wait_for(
            self.context.send_message(self.cfg.target_umo, chain), timeout=20
        )
        if not result:
            raise RuntimeError("Target platform was not found while sending")

    async def terminate(self):
        self.accepting = False
        if self.runner:
            await self.runner.cleanup()
            self.runner = None
            self.site = None
