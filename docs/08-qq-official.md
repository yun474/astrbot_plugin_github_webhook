# QQ 官方机器人 Markdown 推送

这个 fork 由 yun474 维护，原作者为 TatsukiMeng（TatsukiMengChen）。

## 配置

1. 在 AstrBot 中接入 QQ 官方机器人，支持 WebSocket 和 Webhook 两种适配器。
2. 群聊中开启“机器人主动在群聊内发言”，启动后先在目标群 @机器人发送一次消息，让适配器识别会话。
3. 取得目标会话的完整 UMO（消息事件的 `event.unified_msg_origin`），填入插件的 `target_umo`。QQ 官方群聊使用 `group_openid`，不能直接填普通群号。
4. 将 `push_mode` 选为“Markdown 推送”，即可发送原生 Markdown 标题、字段、提交列表和链接。只影响 QQ 官方适配器；其他平台使用普通文本。
5. 在 GitHub 仓库设置 Webhook，指向本插件独立的 `/webhook` 接口，并在两端填写相同的 Secret。这个地址与接收 QQ 消息的回调地址不同。

QQ群 UMO 示例：`official-bot:GroupMessage:群的group_openid`。
QQ 私聊示例：`official-bot:FriendMessage:用户的openid`。
第一个字段是你配置的机器人实例 ID。

原生 Markdown 需要 QQ 账号具备相应权限。AstrBot 对明确的 Markdown 权限拒绝可能降级为文本；插件自身不做盲目重发。也可选择“原生文本”发送普通文本。

## 在通知开头艾特用户

在 `qq_mention_openid` 中填写一个用户 OpenID，例如 `MEMBER_OPENID`。插件自动拼接：

```xml
<qqbot-at-user id="MEMBER_OPENID" />
```

标签位于 Markdown 正文第一行，后面空一行再显示通知标题。留空不艾特，只在 QQ 官方 Markdown 模式下生效。群聊中使用该机器人收到的群成员 OpenID，不能填普通 QQ 号。插件会在 LLM 生成完后添加标签，不会让模型改写这个标签。

## 版本兼容

QQ 官方**主动 Markdown 推送需要 AstrBot >= 4.28.0**。
上游 [#9914](https://github.com/AstrBotDevs/AstrBot/pull/9914) 才让主动发送接口读取 Markdown 标记；
v4.27.5 尚未包含此实现，v4.28.0 已包含。仅有 `MessageChain.use_markdown` 不足以证明主动推送可用。

低于这个版本时，QQ Markdown 模式返回 HTTP 503，并提示升级或选择“原生文本”。
普通文本模式不据此强制提高 AstrBot 最低版本。

本地验证覆盖 Python 3.12、AstrBot 4.28.0 和 4.28.1，使用真实 AstrBot SDK，拦截对腾讯的网络请求，检查群聊/私聊及两种适配器的请求内容。
这不等于真实 QQ 账号验证：主动发言权限、Markdown 权限、URL 配置、发送配额和最终显示效果需要部署后确认。

## 接收与失败处理

- 正常事件入队后立即返回 HTTP 202，表示已接收，**不表示 QQ 已送达**。LLM 生成和发送在后台顺序执行。
- 队列最多等待 100 条通知。队列已满、目标不可用、未填写 UMO 时返回 503；达到每分钟限额时返回 429。
- 签名错误或缺失时返回 401；JSON/事件结构错误返回 400；请求体上限为 1 MiB，超出返回 413。
- `ping`、不支持的事件和重复投递不占用通知限额。
- 通过 `X-GitHub-Delivery` 防止处理中的重复投递；成功记录最多保留 1 小时、1024 条。发送失败会解除去重，允许手动重投。
- 发送失败时，日志会记录 delivery ID。修复原因后，在 GitHub 的 Recent deliveries 中找到对应事件，手动 Redeliver。GitHub 不会自动重投。
- 队列和去重记录只保存在内存中。退出时最多等待 10 秒，剩余任务会记录到日志；进程崩溃或重启后需要检查是否有未发送事件，并手动重投。
- 单次消息发送超时为 20 秒。超时存在实际已发送但响应丢失的可能，手动重投前先看 QQ，避免重复通知。

## 内容

Push 显示提交总数，最多展开 5 条，每条取首行并限制长度。
Issue 和 PR 提供标题链接；PR 已合并时显示“已合并”。
Star 显示操作人、仓库、事件发生时的 Star 总数和仓库链接，支持点星与取消星标。
标题、分支名等动态内容会转义 Markdown，避免意外破坏排版。
选择“LLM 改写”后会要求模型保留 Markdown、事实和链接。`llm_timeout_fallback_md` 开启时，超时会回退原始 Markdown 模板；关闭时不发送该条。鉴权失败、空内容等非超时错误不会自动回退。艾特标签始终在生成之后由插件拼接。

### Star 通知

在 GitHub Webhook 中勾选 **Stars** 并保存。自己给该仓库点星也会触发；已经点过星时，可以取消后重新点星测试，这会产生两条通知。
插件只处理 `star` 的 `created` / `deleted`，不处理 `watch`，同时勾选 Stars 和 Watches 也不会重复推送。

Markdown 示例（配置了艾特时，插件会在标题前添加艾特标签）：

```markdown
# ⭐ 收到新的 Star

**yun474** 点亮了星标

**仓库**：owner/repository

**当前 Star**：42

[查看仓库 →](https://github.com/owner/repository)
```

取消时标题为“💫 有人取消了 Star”，正文改为“取消了星标”。数量直接使用事件中的 `stargazers_count`，不额外请求 GitHub API。三种推送模式、LLM 超时回退和艾特设置均沿用现有配置。
