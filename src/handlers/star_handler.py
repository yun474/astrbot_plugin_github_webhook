"""Extract repository star changes."""

from ..formatters.star_formatter import format_star_message


async def handle_star_event(data: dict, context, markdown: bool = False):
    action = data.get("action")
    if action not in {"created", "deleted"}:
        return None
    repository = data["repository"]
    return format_star_message(
        action=action,
        author_name=data["sender"]["login"],
        repo_name=repository["full_name"],
        star_count=repository["stargazers_count"],
        repo_url=repository["html_url"],
        markdown=markdown,
    )
