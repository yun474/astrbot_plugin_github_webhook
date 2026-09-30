"""Plugin settings, including defaults for existing installations."""

import re

from astrbot.api import logger


class PluginConfig:
    def __init__(self, config):
        self.port = int(config.get("port", 8080))
        self.target_umo = config.get("target_umo", "").strip()
        self.webhook_secret = config.get("webhook_secret", "")
        self.rate_limit = int(config.get("rate_limit", 10))
        self.push_mode = config.get("push_mode", "Markdown 推送")
        self.llm_timeout_fallback_md = config.get("llm_timeout_fallback_md", True)
        self.qq_mention_openid = config.get("qq_mention_openid", "").strip()
        self.llm_provider_id = config.get("llm_provider_id", "")
        self.agent_timeout = int(config.get("agent_timeout", 60))
        self.agent_system_prompt = config.get("agent_system_prompt", "")

        if self.push_mode not in {"原生文本", "Markdown 推送", "LLM 改写"}:
            raise ValueError("push_mode must select exactly one supported mode")

        if self.qq_mention_openid and not re.fullmatch(
            r"[A-Za-z0-9_-]+", self.qq_mention_openid
        ):
            raise ValueError("qq_mention_openid must be an OpenID, not an @ tag")

        if not 0 <= self.port <= 65535:
            raise ValueError("port must be between 0 and 65535")
        if self.rate_limit < 0 or self.agent_timeout <= 0:
            raise ValueError(
                "rate_limit must be nonnegative and agent_timeout positive"
            )
        if self.target_umo:
            parts = self.target_umo.split(":", 2)
            if len(parts) != 3 or not all(parts):
                raise ValueError("target_umo must be the complete unified_msg_origin")
        else:
            logger.warning("GitHub Webhook: target_umo is not configured")
        if not self.webhook_secret:
            logger.warning("GitHub Webhook: signature verification is disabled")
