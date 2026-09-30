"""Build pull request notifications."""

from .markdown import escape_text, link


def format_pull_request_message(
    action: str,
    author_name: str,
    repo_name: str,
    pr_number: int,
    title: str,
    base_branch: str,
    head_branch: str,
    pr_url: str,
    markdown: bool = False,
) -> str:
    title = " ".join(title.split())[:200]
    if markdown:
        status = {
            "opened": "新建",
            "closed": "关闭",
            "reopened": "重新打开",
            "synchronize": "更新提交",
            "merged": "已合并",
        }.get(action, action)
        return "\n\n".join(
            [
                "# 🔀 GitHub Pull Request",
                f"**仓库**：{escape_text(repo_name)}",
                f"**操作**：{escape_text(author_name)} · {escape_text(status)}",
                f"**分支**：{escape_text(head_branch)} → {escape_text(base_branch)}",
                link(f"#{pr_number} {title}", pr_url),
            ]
        )
    return (
        f"🔀 GitHub Pull Request Event\n"
        f"👤 {author_name} {action} PR in {repo_name}\n"
        f"📋 PR #{pr_number}: {title}\n"
        f"🌿 {head_branch} → {base_branch}\n"
        f"📎 {pr_url}"
    )
