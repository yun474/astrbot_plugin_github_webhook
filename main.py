"""AstrBot GitHub Webhook plugin entry point."""

from astrbot.api.star import Context, Star, register

from .src.core.plugin import GitHubWebhookPlugin


@register(
    "astrbot_plugin_github_webhook",
    "TatsukiMeng, yun474",
    "GitHub Webhook 通知，支持 QQ 官方机器人 Markdown 推送",
    "0.5.1",
)
class PluginEntry(Star):
    """Manage the webhook receiver with the AstrBot plugin lifecycle."""

    def __init__(self, context: Context, config):
        super().__init__(context)
        self._plugin = GitHubWebhookPlugin(context, config)

    async def initialize(self):
        await self._plugin.start_server()

    async def terminate(self):
        await self._plugin.terminate()
