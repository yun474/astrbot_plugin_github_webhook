# 配置说明

配置修改后重新加载插件。

## 基础设置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `port` | `8080` | 接收 GitHub Webhook 的端口 |
| `target_umo` | 空 | 完整会话标识 `platform_id:message_type:session_id` |
| `webhook_secret` | 空 | 与 GitHub 设置相同的签名密钥；留空不验签 |
| `rate_limit` | `10` | 每分钟接受的通知数；0 表示不限 |

UMO 使用 `event.unified_msg_origin`；也可以在目标会话调用 `/sid` 获取。
QQ 官方群聊的会话 ID 是 `group_openid`，私聊是用户 OpenID，不能替换成普通 QQ 号或群号。

## 推送模式

`push_mode` 是单选项，三个模式互斥：

| 模式 | 行为 |
| --- | --- |
| 原生文本 | 直接发送普通文本事件摘要，不调用 LLM |
| Markdown 推送（默认） | 发送带标题、字段、列表和链接的事件模板，不调用 LLM |
| LLM 改写 | 将事件摘要交给模型改写，再发送生成结果 |

QQ 官方适配器的 Markdown 和 LLM 模式使用原生 Markdown，需要 AstrBot >= 4.28.0。
其他平台发送普通文本模板或普通文本的 LLM 改写结果。

旧版的 `enable_agent` 和 `qq_official_markdown` 独立开关已被单选模式取代；升级后请重新选择所需模式。

## 艾特用户

`qq_mention_openid` 默认留空。

填写要艾特的用户 OpenID 后，插件会在 QQ 官方 Markdown 消息最前面拼接：

```xml
<qqbot-at-user id="填写的OpenID" />
```

标签后面空一行，再接通知正文。群聊中应填写该机器人收到的群成员 OpenID。
不要填写普通 QQ 号或完整标签。留空不艾特；原生文本和其他平台不插入这个标签。

LLM 模式下，艾特标签由插件在改写完成后添加。模型只负责正文。
超时回退模板也会添加同样的前缀。

## LLM 设置

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `llm_provider_id` | 空 | 模型提供商 ID；空值使用目标会话的默认模型 |
| `agent_timeout` | `60` | 模型选择和生成的总超时时间，单位秒 |
| `agent_system_prompt` | 空 | 自定义系统提示词，用于控制正文语气 |
| `llm_timeout_fallback_md` | `true` | 超时时是否回退 Markdown 模板 |

超时回退开关只在“LLM 改写”模式生效：

- 开启：LLM 超时后发送原始 Markdown 模板，并由插件添加配置的艾特前缀。
- 关闭：该条不发送，记录失败并允许手动重投。
- 非超时错误（例如鉴权失败、返回空内容）不会触发这个开关，也会记录失败。
- 其他平台超时回退时使用普通文本模板。

更完整的投递说明见 [QQ 官方说明](08-qq-official.md)。
