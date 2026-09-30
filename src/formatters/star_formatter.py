"""Build notifications for stars added to or removed from a repository."""

from .markdown import escape_text, link


def format_star_message(
    action: str,
    author_name: str,
    repo_name: str,
    star_count: int,
    repo_url: str,
    markdown: bool = False,
) -> str:
    created = action == "created"
    title = "⭐ 收到新的 Star" if created else "💫 有人取消了 Star"
    status = "点亮了星标" if created else "取消了星标"
    if markdown:
        return "\n\n".join(
            [
                f"# {title}",
                f"**{escape_text(author_name)}** {status}",
                f"**仓库**：{escape_text(repo_name)}",
                f"**当前 Star**：{escape_text(str(star_count))}",
                link("查看仓库 →", repo_url),
            ]
        )
    return (
        f"{title}\n"
        f"{author_name} {status}\n"
        f"仓库：{repo_name}\n"
        f"当前 Star：{star_count}\n"
        f"📎 {repo_url}"
    )
