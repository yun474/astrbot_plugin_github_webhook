"""Extract push details without losing additional commits."""

from ..formatters.push_formatter import format_push_message


async def handle_push_event(data: dict, context, markdown: bool = False):
    commits = data["commits"]
    if not isinstance(commits, list):
        raise ValueError("commits must be a list")
    if not commits:
        return None
    return format_push_message(
        author_name=data.get("pusher", {}).get("name", "Unknown"),
        repo_name=data["repository"]["full_name"],
        branch=data.get("ref", "").removeprefix("refs/heads/"),
        commits=commits,
        markdown=markdown,
    )
