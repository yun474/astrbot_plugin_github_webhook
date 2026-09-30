"""Build compact push notifications."""

from .markdown import escape_text, link


def format_push_message(
    author_name: str,
    repo_name: str,
    branch: str,
    commits: list,
    markdown: bool = False,
) -> str:
    if markdown:
        lines = [
            "# 📦 GitHub Push",
            f"**仓库**：{escape_text(repo_name)}",
            f"**推送者**：{escape_text(author_name)}",
            f"**分支**：{escape_text(branch)}",
            f"**提交**：{len(commits)} 条",
        ]
    else:
        lines = [
            "📦 GitHub Push Event",
            f"👤 {author_name} pushed to {repo_name}",
            f"🌿 Branch: {branch}",
            f"提交：{len(commits)} 条",
        ]
    for commit in commits[:5]:
        commit_id = commit.get("id", "")[:7] or "commit"
        title = (commit.get("message") or "No message").splitlines()[0][:200]
        url = commit.get("url", "")
        if markdown:
            lines.append(f"- {link(commit_id, url)} {escape_text(title)}")
        else:
            lines.append(f"• {commit_id} {title}\n{url}")
    if len(commits) > 5:
        lines.append(f"另有 {len(commits) - 5} 条提交未展开")
    return "\n\n".join(lines) if markdown else "\n".join(lines)
