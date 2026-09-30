"""Verify star events through the signed webhook and shared delivery pipeline."""

from types import SimpleNamespace

import pytest

from src.handlers.star_handler import handle_star_event
from tests.test_webhook import post

STAR = {
    "action": "created",
    "sender": {"login": "yun474"},
    "repository": {
        "full_name": "owner/repository",
        "html_url": "https://github.com/owner/repository",
        "stargazers_count": 42,
    },
    "starred_at": "2026-10-01T00:00:00Z",
}


@pytest.mark.parametrize(
    "action,count,title,status",
    [
        ("created", 42, "⭐ 收到新的 Star", "点亮了星标"),
        ("deleted", 0, "💫 有人取消了 Star", "取消了星标"),
    ],
)
@pytest.mark.parametrize("mode", ["原生文本", "Markdown 推送", "LLM 改写"])
async def test_star_delivery_modes(receiver, action, count, title, status, mode):
    plugin, client = receiver
    plugin.cfg.push_mode = mode
    plugin.cfg.qq_mention_openid = "MEMBER_OPENID"
    plugin.context.llm_generate.return_value = SimpleNamespace(
        completion_text="# 改写后的 Star 通知"
    )
    payload = dict(
        STAR,
        action=action,
        repository=dict(STAR["repository"], stargazers_count=count),
        starred_at=STAR["starred_at"] if action == "created" else None,
    )
    assert (await post(client, payload=payload, event="star")).status == 202
    await plugin.queue.join()
    umo, chain = plugin.context.send_message.call_args.args
    assert umo == "test:GroupMessage:group-openid"
    assert chain.use_markdown_ is (mode != "原生文本")
    text = chain.get_plain_text()
    if mode == "LLM 改写":
        assert text.endswith("# 改写后的 Star 通知")
        template = plugin.context.llm_generate.call_args.kwargs["prompt"]
    else:
        plugin.context.llm_generate.assert_not_called()
        template = text
    assert title in template
    assert status in template
    assert "yun474" in template
    assert "owner/repository" in template
    assert "https://github.com/owner/repository" in template
    if mode == "原生文本":
        assert f"当前 Star：{count}" in template
        assert "qqbot-at-user" not in text
        assert "**" not in text
    else:
        assert f"**当前 Star**：{count}" in template
        assert text.startswith('<qqbot-at-user id="MEMBER_OPENID" />\n\n# ')
        assert text.count("<qqbot-at-user") == 1
    # A repeated delivery is acknowledged without a second notification.
    assert (await post(client, payload=payload, event="star")).status == 200
    assert plugin.context.send_message.call_count == 1


async def test_watch_and_unknown_star_actions_are_ignored(receiver):
    plugin, client = receiver
    for event, action in [("watch", "started"), ("star", "unknown")]:
        response = await post(client, payload=dict(STAR, action=action), event=event)
        assert response.status == 204
    assert plugin.rate_limiter.get_usage()[0] == 0
    plugin.context.send_message.assert_not_called()


async def test_incomplete_star_payload_is_rejected(receiver):
    plugin, client = receiver
    assert (
        await post(client, payload={"action": "created"}, event="star")
    ).status == 400
    assert plugin.rate_limiter.get_usage()[0] == 0
    plugin.context.send_message.assert_not_called()


async def test_star_markdown_escapes_fields_and_rejects_unsafe_link():
    text = await handle_star_event(
        dict(
            STAR,
            sender={"login": "[user](bad)"},
            repository=dict(
                STAR["repository"],
                full_name="owner/*repo*\n# injected",
                html_url="javascript:alert(1)",
            ),
        ),
        None,
        markdown=True,
    )
    assert r"\[user\]\(bad\)" in text
    assert r"owner/\*repo\* \# injected" in text
    assert "javascript:" not in text
    assert text.endswith("查看仓库 →")
