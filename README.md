# AstrBot GitHub Webhook Plugin

AstrBot 插件，用于接收 GitHub 事件（push、issues、pull requests 等）并转发到聊天平台（QQ 群组、私聊等）。

## 功能特性

- ✅ QQ 官方机器人原生 Markdown 推送（群聊、私聊）
- ✅ 后台通知队列、签名校验、重复投递去重
- ✅ 接收 GitHub Webhook 事件
- ✅ 支持 Push 事件（代码提交）
- ✅ 支持 Issues 事件（问题追踪）
- ✅ 支持 Pull Request 事件（代码合并）
- ✅ 支持 Stars 事件（点星、取消星标）
- ✅ 实时转发到指定的聊天平台群组/用户
- ✅ 自定义端口号配置
- ✅ 简洁的消息格式，包含关键信息
- ✅ Webhook Secret 签名验证（防止恶意请求）
- ✅ 请求速率限制（防止消息轰炸）
- ✅ 全面的错误处理和日志记录
- ✅ LLM 智能消息生成（支持自定义提示词）
- 🔜 自定义消息模板
- 🔜 Release 事件支持

## 快速开始

### 安装

```bash
cd AstrBot/data/plugins
git clone https://github.com/yun474/astrbot_plugin_github_webhook.git
cd astrbot_plugin_github_webhook
pip install -r requirements.txt
```

### 配置

在 AstrBot WebUI 中配置插件，或编辑配置文件：

`data/config/astrbot_plugin_github_webhook_config.json`

```json
{
  "port": 8080,
  "target_umo": "platform_id:GroupMessage:群号",
  "webhook_secret": "your_github_webhook_secret",
  "rate_limit": 10,
  "push_mode": "Markdown 推送",
  "qq_mention_openid": "",
  "llm_timeout_fallback_md": true,
  "llm_provider_id": "",
  "agent_timeout": 60,
  "agent_system_prompt": ""
}
```

### 重启

```bash
sudo systemctl restart astrbot
# 或手动重启 AstrBot
```

查看日志确认插件已加载：

```
[INFO] GitHub Webhook server started on port 8080
```

### 配置 GitHub Webhook

1. 进入 GitHub 仓库 → **Settings** → **Webhooks** → **Add webhook**
2. **Payload URL**: `http://你的服务器IP:8080/webhook`
3. **Content type**: `application/json`
4. **Secret** (可选): 配置 Webhook 密钥用于签名验证
5. **Events**: 选择需要触发的事件（Pushes、Issues、Pull requests、Stars）；点星通知勾选 **Stars** 即可，插件不处理 Watches，避免同一次点星重复通知。
6. **Active**: ✅ 勾选
7. 点击 "Add webhook"

## QQ 官方 Markdown 推送

推送模式单选：**原生文本 / Markdown 推送 / LLM 改写**。LLM 超时是否回退 Markdown 由独立开关控制。

QQ 官方主动 Markdown 需要 **AstrBot >= 4.28.0**。开启群聊主动发言，并使用完整 UMO；QQ 官方会话使用 OpenID，不是普通 QQ 号或群号。

需要通知时艾特某人，可在 `qq_mention_openid` 填写用户 OpenID；插件自动在 Markdown 开头拼接完整标签，留空则不艾特。

详见 [QQ 官方配置与投递说明](docs/08-qq-official.md)。接收成功返回 HTTP 202，表示事件入队；发送结果请查看日志。

## 文档

详细的配置、使用和部署文档请查看 [docs/](docs/) 目录：

- [文档索引](docs/index.md) - 文档导航中心
- [安装指南](docs/01-installation.md) - 详细安装步骤
- [配置说明](docs/02-configuration.md) - 所有配置项详解
- [使用示例](docs/03-usage.md) - 查看各种事件的消息格式
- [部署指南](docs/04-deployment.md) - 防火墙、Docker 部署
- [故障排查](docs/05-troubleshooting.md) - 常见问题解决方案
- [项目结构](docs/07-project-structure.md) - 代码组织和设计理念
- [开发相关](docs/06-development.md) - 贡献指南和路线图

## LLM Prompt 示例

在 `templates/` 目录中提供了预置的系统提示词：

- [默认 Prompt](templates/default.md) - 通用 GitHub 事件消息生成提示词

## 目录结构

```
astrbot_plugin_github_webhook/
├── src/                          # Python 源代码
│   ├── core/                 # 核心管理
│   ├── handlers/              # 事件处理
│   ├── formatters/             # 消息格式化
│   ├── utils/                 # 工具函数
│   └── services/              # 业务服务
├── main.py                     # 插件入口
├── metadata.yaml               # 插件元数据
├── _conf_schema.json           # 配置 Schema
├── docs/                      # 详细文档
├── templates/                 # Prompt 模板
├── tests/                     # 测试代码
├── LICENSE                    # MIT 许可证
└── README.md                  # 本文件
```

详见 [项目结构文档](docs/07-project-structure.md)

## 依赖

- [aiohttp](https://docs.aiohttp.org/) ≥ 3.11.0 - 异步 HTTP 服务器

## 开发计划

- [x] Issues 事件支持
- [x] Pull Request 事件支持
- [ ] Release 事件支持
- [x] Webhook Secret 签名验证
- [x] 请求速率限制
- [ ] 自定义消息模板（Jinja2）
- [x] Agent 集成（智能消息生成）
- [ ] 分支过滤（仅监听 main 分支）
- [ ] 多目标支持（不同事件发到不同群组）

## 贡献

欢迎提交 Issue 和 Pull Request！详见 [开发文档](docs/06-development.md)。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 作者

原作者：[TatsukiMeng（TatsukiMengChen）](https://github.com/TatsukiMeng)

Fork 维护：[yun474](https://github.com/yun474)

## 致谢

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) - 强大的聊天机器人框架
- [GitHub Webhooks](https://docs.github.com/en/developers/webhooks-and-events/webhooks) - GitHub 官方文档

## 相关链接

- [AstrBot 文档](https://docs.astrbot.net)
- [AstrBot 插件开发指南](https://docs.astrbot.net/dev/star/introduction)
- [GitHub Webhooks 文档](https://docs.github.com/en/developers/webhooks-and-events/webhooks)

## 本地验证

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check .
ruff format --check .
```

测试使用真实 AstrBot SDK，并拦截外部模型和 QQ API 调用；不会向真实群聊发消息。
