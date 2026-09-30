# 故障排查

## GitHub 显示成功，QQ 没有通知

HTTP 202 只表示进入后台队列。先在 AstrBot 日志中搜索 `GitHub Webhook` 和该次投递的 `X-GitHub-Delivery`。

- `delivery failed`：修复日志中报告的模型或平台错误，然后在 GitHub Recent deliveries 中手动重投。
- `interrupted delivery` / `unsent on shutdown`：任务在关闭时未完成，需要检查 QQ 后手动重投。
- 框架出现 `No cached msg_id`：启动后先在目标群 @机器人发一条消息，让适配器识别群聊。
- 检查完整 UMO、群聊主动发言权限、Markdown 权限和消息 URL 配置。平台接口返回成功不代表客户端已展示。

## 返回 401

在 GitHub 和插件中填写相同 Secret。配置了 Secret 后，缺少签名或签名不匹配都会被拒绝。
不要用删除签名头的办法绕过验签。

## 返回 400 / 413

400 表示 JSON 或事件字段无效；413 表示请求体超过 1 MiB。

## 返回 429 / 503

429 是每分钟接收限额。503 可能是目标平台不存在、未配置完整 UMO、队列满或 QQ Markdown 所需的 AstrBot 版本不足。响应正文会说明原因。
GitHub 不会自动重投这些事件。

## LLM 超时或报错

确认单选推送模式为“LLM 改写”，并检查模型配置及 `agent_timeout`。
超时时，`llm_timeout_fallback_md` 开启会发送模板，关闭则记录失败而不发送。
鉴权错误、模型返回空内容等非超时错误不触发这个回退开关。

## 艾特显示成文字或没有提醒

只填写用户 OpenID，不填写完整标签或普通 QQ 号。QQ群中使用该机器人收到的群成员 OpenID。
原生文本模式不插入标签；Markdown 和 LLM 模式由插件统一添加。
检查 QQ 账号权限和实际发送模式；平台降级为文本时，展示效果由 QQ 决定。

## 重复通知

插件按 delivery ID 对处理中的事件和最近成功事件去重，记录保留最多 1 小时、1024 条。
重启会清空记录。发送请求超时也可能实际已经送达，重投前先检查 QQ。
