"""Build issue notifications."""

from .markdown import escape_text, link


def format_issue_message(
    action: str,
    author_name: str,
    repo_name: str,
    issue_number: int,
    title: str,
    issue_url: str,
    markdown: bool = False,
) -> str:
    title = " ".join(title.split())[:200]
    if markdown:
        status = {"opened": "新建", "closed": "关闭", "reopened": "重新打开"}.get(
            action, action
        )
        return "\n\n".join(
            [
                "# 📋 GitHub Issue",
                f"**仓库**：{escape_text(repo_name)}",
                f"**操作**：{escape_text(author_name)} · {escape_text(status)}",
                link(f"#{issue_number} {title}", issue_url),
            ]
        )
    return (
        f"📋 GitHub Issue Event\n"
        f"👤 {author_name} {action} issue in {repo_name}\n"
        f"Issue #{issue_number}: {title}\n"
        f"📎 {issue_url}"
    )
