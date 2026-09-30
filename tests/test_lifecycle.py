"""Load the plugin as AstrBot does and release its listener and worker."""

import asyncio
import importlib.util
import sys
from pathlib import Path

import aiohttp

from src.core.plugin import GitHubWebhookPlugin


async def test_package_import_and_plugin_lifecycle(context):
    root = Path(__file__).parents[1]
    module_name = "github_webhook_isolated"
    spec = importlib.util.spec_from_file_location(
        module_name, root / "main.py", submodule_search_locations=[str(root)]
    )
    module = importlib.util.module_from_spec(spec)
    original_path = list(sys.path)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        assert sys.path == original_path
        plugin = module.PluginEntry(
            context,
            {
                "port": 0,
                "target_umo": "test:GroupMessage:group-openid",
            },
        )
        assert plugin.context is context
        await plugin.initialize()
        port = plugin._plugin.site._server.sockets[0].getsockname()[1]
        async with aiohttp.ClientSession() as client:
            response = await client.post(
                f"http://127.0.0.1:{port}/webhook",
                json={},
                headers={"X-GitHub-Event": "ping"},
            )
            assert response.status == 200
        await plugin.terminate()
        await plugin.terminate()
        assert plugin._plugin.runner is None
    finally:
        for key in list(sys.modules):
            if key == module_name or key.startswith(module_name + "."):
                del sys.modules[key]


async def test_shutdown_cancels_slow_delivery_and_clears_pending_queue(context):
    plugin = GitHubWebhookPlugin(
        context,
        {
            "port": 0,
            "target_umo": "test:GroupMessage:group-openid",
        },
    )
    plugin.shutdown_timeout = 0.01
    started = asyncio.Event()

    async def blocked_send(*args):
        started.set()
        await asyncio.Event().wait()

    context.send_message.side_effect = blocked_send
    await plugin.start_server()
    plugin.pending_deliveries.update({"active", "waiting"})
    plugin.queue.put_nowait(("active", "push", "first", False))
    await asyncio.wait_for(started.wait(), 1)
    plugin.queue.put_nowait(("waiting", "push", "second", False))
    await asyncio.wait_for(plugin.terminate(), 1)
    assert not plugin.accepting
    assert not plugin.pending_deliveries
    assert plugin.queue.empty()
    await asyncio.wait_for(plugin.queue.join(), 1)
