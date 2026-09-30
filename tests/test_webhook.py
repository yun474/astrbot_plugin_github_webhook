"""Exercise HTTP acceptance, authentication, queueing and delivery failures."""

import asyncio
import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest

PUSH = {
    "repository": {"full_name": "yun474/example"},
    "pusher": {"name": "yun474"},
    "ref": "refs/heads/main",
    "commits": [
        {
            "id": "abcdef012345",
            "message": "修复通知",
            "url": "https://github.com/yun474/example/commit/abcdef0",
        },
        {
            "id": "123456789abc",
            "message": "增加测试",
            "url": "https://github.com/yun474/example/commit/1234567",
        },
    ],
}


async def post(
    client, payload=PUSH, delivery="delivery-1", event="push", signature=True
):
    body = json.dumps(payload).encode()
    headers = {"X-GitHub-Event": event, "X-GitHub-Delivery": delivery}
    if signature:
        digest = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        headers["X-Hub-Signature-256"] = f"sha256={digest}"
    return await client.post("/webhook", data=body, headers=headers)


async def test_missing_signature_is_rejected_without_using_quota(receiver):
    plugin, client = receiver
    assert (await post(client, signature=False)).status == 401
    assert plugin.rate_limiter.get_usage()[0] == 0
    plugin.context.send_message.assert_not_called()


async def test_wrong_signature_is_rejected(receiver):
    plugin, client = receiver
    response = await client.post(
        "/webhook",
        data=json.dumps(PUSH),
        headers={
            "X-GitHub-Event": "push",
            "X-Hub-Signature-256": "sha256=wrong",
        },
    )
    assert response.status == 401
    plugin.context.send_message.assert_not_called()


async def test_signed_event_produces_native_markdown(receiver):
    plugin, client = receiver
    assert (await post(client)).status == 202
    await plugin.queue.join()
    umo, chain = plugin.context.send_message.call_args.args
    assert umo == "test:GroupMessage:group-openid"
    assert chain.use_markdown_ is True
    assert "# 📦 GitHub Push" in chain.get_plain_text()
    assert "abcdef0" in chain.get_plain_text()
    assert "1234567" in chain.get_plain_text()


@pytest.mark.parametrize(
    "platform_name,enabled",
    [
        ("qq_official_webhook", False),
        ("aiocqhttp", True),
    ],
)
async def test_plain_text_mode(receiver, platform_name, enabled):
    plugin, client = receiver
    plugin.cfg.push_mode = "Markdown 推送" if enabled else "原生文本"
    plugin.context.get_platform_inst = lambda _: SimpleNamespace(
        meta=lambda: SimpleNamespace(name=platform_name)
    )
    assert (await post(client)).status == 202
    await plugin.queue.join()
    chain = plugin.context.send_message.call_args.args[1]
    assert chain.use_markdown_ is False
    assert not chain.get_plain_text().startswith("# ")


@pytest.mark.parametrize("payload", [[], None, {}, {"commits": "wrong"}])
async def test_invalid_payload_does_not_use_quota(receiver, payload):
    plugin, client = receiver
    assert (await post(client, payload=payload)).status == 400
    assert plugin.rate_limiter.get_usage()[0] == 0


async def test_invalid_json_and_large_payload_keep_correct_http_errors(receiver):
    plugin, client = receiver
    plugin.cfg.webhook_secret = ""
    assert (await client.post("/webhook", data=b"{")).status == 400
    assert (await client.post("/webhook", data=b"x" * (1024 * 1024 + 1))).status == 413


async def test_ping_and_unsupported_events_do_not_use_quota(receiver):
    plugin, client = receiver
    assert (await post(client, payload={}, event="ping")).status == 200
    assert (await post(client, payload={}, event="release")).status == 204
    assert plugin.rate_limiter.get_usage()[0] == 0


async def test_unavailable_target_is_reported(receiver):
    plugin, client = receiver
    plugin.context.get_platform_inst = lambda _: None
    assert (await post(client)).status == 503


async def test_slow_llm_does_not_delay_ack_or_duplicate_pending_delivery(receiver):
    plugin, client = receiver
    plugin.cfg.push_mode = "LLM 改写"
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_model(**kwargs):
        started.set()
        await release.wait()
        return SimpleNamespace(
            completion_text="# 生成结果\n\n[提交](https://github.com/x/y)"
        )

    plugin.context.llm_generate.side_effect = slow_model
    try:
        response = await asyncio.wait_for(post(client), 1)
        assert response.status == 202
        await asyncio.wait_for(started.wait(), 1)
        plugin.context.send_message.assert_not_called()
        assert (await post(client)).status == 200
    finally:
        release.set()
    await plugin.queue.join()
    assert (await post(client)).status == 200
    assert plugin.context.send_message.call_count == 1
    assert plugin.context.llm_generate.call_count == 1


async def test_llm_failure_falls_back_once(receiver):
    plugin, client = receiver
    plugin.cfg.push_mode = "LLM 改写"
    plugin.context.llm_generate.side_effect = TimeoutError("model timeout")
    assert (await post(client)).status == 202
    await plugin.queue.join()
    assert plugin.context.send_message.call_count == 1
    assert (
        "GitHub Push" in plugin.context.send_message.call_args.args[1].get_plain_text()
    )


async def test_failed_send_can_be_redelivered_without_second_llm_fallback(receiver):
    plugin, client = receiver
    plugin.cfg.push_mode = "LLM 改写"
    plugin.context.llm_generate.return_value = SimpleNamespace(completion_text="# 通知")
    plugin.context.send_message.side_effect = RuntimeError("QQ rejected request")
    assert (await post(client)).status == 202
    await plugin.queue.join()
    assert plugin.context.send_message.call_count == 1
    assert "delivery-1" not in plugin.completed_deliveries
    plugin.context.send_message.side_effect = None
    assert (await post(client)).status == 202
    await plugin.queue.join()
    assert plugin.context.send_message.call_count == 2


async def test_false_send_result_is_not_marked_delivered(receiver):
    plugin, client = receiver
    plugin.context.send_message.return_value = False
    assert (await post(client)).status == 202
    await plugin.queue.join()
    assert not plugin.completed_deliveries


async def test_rate_limit_and_duplicate_delivery(receiver):
    plugin, client = receiver
    plugin.rate_limiter.max_requests = 1
    assert (await post(client)).status == 202
    await plugin.queue.join()
    assert (await post(client)).status == 200
    response = await post(client, delivery="second")
    assert response.status == 429
    assert int(response.headers["Retry-After"]) > 0


async def test_queue_capacity_rejects_excess_without_marking_delivery(receiver):
    plugin, client = receiver
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_send(*args):
        started.set()
        await release.wait()
        return True

    plugin.context.send_message.side_effect = slow_send
    try:
        assert (await post(client)).status == 202
        await asyncio.wait_for(started.wait(), 1)
        for index in range(plugin.queue.maxsize):
            plugin.queue.put_nowait((f"queued-{index}", "push", "notification", False))
        assert (await post(client, delivery="overflow")).status == 503
        assert "overflow" not in plugin.pending_deliveries
    finally:
        release.set()


async def test_missing_target_is_not_accepted(receiver):
    plugin, client = receiver
    plugin.cfg.target_umo = ""
    assert (await post(client)).status == 503


async def test_old_astrbot_requires_disabling_qq_markdown(receiver):
    plugin, client = receiver
    plugin.supports_qq_markdown = False
    response = await post(client)
    assert response.status == 503
    assert "4.28.0" in await response.text()
    plugin.cfg.push_mode = "原生文本"
    assert (await post(client)).status == 202
    await plugin.queue.join()
    assert plugin.context.send_message.call_args.args[1].use_markdown_ is False


@pytest.mark.parametrize("with_llm", [False, True])
async def test_mention_prefix_is_added_after_llm(receiver, with_llm):
    plugin, client = receiver
    plugin.cfg.qq_mention_openid = "MEMBER_OPENID"
    plugin.cfg.push_mode = "LLM 改写" if with_llm else "Markdown 推送"
    plugin.context.llm_generate.return_value = SimpleNamespace(
        completion_text="# LLM result"
    )
    assert (await post(client)).status == 202
    await plugin.queue.join()
    text = plugin.context.send_message.call_args.args[1].get_plain_text()
    assert text.startswith('<qqbot-at-user id="MEMBER_OPENID" />\n\n# ')
    assert text.count("<qqbot-at-user") == 1
    if with_llm:
        assert text.endswith("# LLM result")
        assert (
            "<qqbot-at-user"
            not in plugin.context.llm_generate.call_args.kwargs["prompt"]
        )


async def test_mention_is_not_inserted_into_plain_text(receiver):
    plugin, client = receiver
    plugin.cfg.qq_mention_openid = "MEMBER_OPENID"
    plugin.cfg.push_mode = "原生文本"
    assert (await post(client)).status == 202
    await plugin.queue.join()
    assert (
        "qqbot-at-user"
        not in plugin.context.send_message.call_args.args[1].get_plain_text()
    )


@pytest.mark.parametrize(
    "mode,uses_llm,uses_markdown",
    [
        ("原生文本", False, False),
        ("Markdown 推送", False, True),
        ("LLM 改写", True, True),
    ],
)
async def test_push_modes_are_exclusive(receiver, mode, uses_llm, uses_markdown):
    plugin, client = receiver
    plugin.cfg.push_mode = mode
    plugin.context.llm_generate.return_value = SimpleNamespace(
        completion_text="# AI notification"
    )
    assert (await post(client)).status == 202
    await plugin.queue.join()
    assert plugin.context.llm_generate.call_count == int(uses_llm)
    assert plugin.context.send_message.call_count == 1
    chain = plugin.context.send_message.call_args.args[1]
    assert chain.use_markdown_ is uses_markdown
    assert ("AI notification" in chain.get_plain_text()) is uses_llm


@pytest.mark.parametrize("fallback_enabled", [True, False])
async def test_actual_llm_timeout_obeys_fallback_switch(receiver, fallback_enabled):
    plugin, client = receiver
    plugin.cfg.push_mode = "LLM 改写"
    plugin.cfg.llm_timeout_fallback_md = fallback_enabled
    plugin.cfg.qq_mention_openid = "MEMBER_OPENID"
    plugin.cfg.agent_timeout = 0.01
    cancelled = asyncio.Event()

    async def blocked_model(**kwargs):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    plugin.context.llm_generate.side_effect = blocked_model
    assert (await post(client)).status == 202
    await asyncio.wait_for(plugin.queue.join(), 1)
    assert cancelled.is_set()
    assert plugin.context.send_message.call_count == int(fallback_enabled)
    assert ("delivery-1" in plugin.completed_deliveries) is fallback_enabled
    if fallback_enabled:
        chain = plugin.context.send_message.call_args.args[1]
        assert chain.use_markdown_ is True
        assert chain.get_plain_text().startswith(
            '<qqbot-at-user id="MEMBER_OPENID" />\n\n# 📦'
        )
    else:
        assert "delivery-1" not in plugin.pending_deliveries


@pytest.mark.parametrize("failure", [RuntimeError("invalid model key"), None])
async def test_non_timeout_model_failure_does_not_trigger_timeout_fallback(
    receiver, failure
):
    plugin, client = receiver
    plugin.cfg.push_mode = "LLM 改写"
    if failure:
        plugin.context.llm_generate.side_effect = failure
    else:
        plugin.context.llm_generate.return_value = SimpleNamespace(completion_text="  ")
    assert (await post(client)).status == 202
    await plugin.queue.join()
    plugin.context.send_message.assert_not_called()
    assert not plugin.completed_deliveries
