"""Use the real AstrBot SDK, with only network services replaced."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from src.core.plugin import GitHubWebhookPlugin


@pytest.fixture
def context():
    platform = SimpleNamespace(meta=lambda: SimpleNamespace(name="qq_official_webhook"))
    return SimpleNamespace(
        get_platform_inst=lambda platform_id: platform,
        send_message=AsyncMock(return_value=True),
        get_current_chat_provider_id=AsyncMock(return_value="test-model"),
        llm_generate=AsyncMock(),
    )


@pytest.fixture
async def receiver(context):
    plugin = GitHubWebhookPlugin(
        context,
        {
            "target_umo": "test:GroupMessage:group-openid",
            "webhook_secret": "test-secret",
        },
    )
    async with TestClient(TestServer(plugin.app)) as client:
        yield plugin, client
