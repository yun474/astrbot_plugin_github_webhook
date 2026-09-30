"""Verify SDK-generated QQ request bodies without contacting Tencent."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from astrbot.core.platform.message_session import MessageSession
from astrbot.core.platform.sources.qqofficial.qqofficial_platform_adapter import (
    QQOfficialPlatformAdapter,
)
from astrbot.core.platform.sources.qqofficial_webhook.qo_webhook_adapter import (
    QQOfficialWebhookPlatformAdapter,
)

from src.core.plugin import GitHubWebhookPlugin


@pytest.mark.parametrize(
    "adapter_type",
    [
        QQOfficialPlatformAdapter,
        QQOfficialWebhookPlatformAdapter,
    ],
)
@pytest.mark.parametrize(
    "scene,method,umo",
    [
        ("group", "post_group_message", "test:GroupMessage:group-openid"),
        ("friend", "post_c2c_message", "test:FriendMessage:user-openid"),
    ],
)
@pytest.mark.parametrize("markdown", [True, False])
async def test_real_adapter_payload(
    adapter_type, scene, method, umo, markdown, monkeypatch
):
    monkeypatch.setattr("astrbot.core.platform.platform.Metric.upload", AsyncMock())
    adapter = object.__new__(adapter_type)
    adapter._session_scene = {"group-openid": scene, "user-openid": scene}
    adapter._session_last_message_id = {}
    adapter._allow_group_proactive_send = True
    adapter.use_markdown_default = not markdown
    adapter.config = {"id": "test"}
    send = AsyncMock(return_value={"id": "sent-message"})
    adapter.client = SimpleNamespace(
        api=SimpleNamespace(**{method: send}, _http=SimpleNamespace(request=send))
    )

    async def send_through_adapter(target, chain):
        await adapter.send_by_session(MessageSession.from_str(target), chain)
        return True

    plugin = GitHubWebhookPlugin(
        SimpleNamespace(send_message=send_through_adapter),
        {"target_umo": umo, "qq_mention_openid": "MEMBER_OPENID"},
    )
    await plugin.send_message("# 仓库更新\n\n**状态**：已合并", markdown)
    payload = send.call_args.kwargs
    if scene == "friend":
        payload = payload["json"]
    if markdown:
        assert payload["msg_type"] == 2
        assert "# 仓库更新" in payload["markdown"]["content"]
        assert payload["markdown"]["content"].startswith(
            '<qqbot-at-user id="MEMBER_OPENID" />\n\n# '
        )
        assert not payload.get("content")
    else:
        assert not payload.get("markdown")
        assert "# 仓库更新" in payload["content"]
        assert "qqbot-at-user" not in payload["content"]
    assert "msg_id" not in payload
