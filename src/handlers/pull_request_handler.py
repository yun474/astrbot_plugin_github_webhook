"""Distinguish merged pull requests from closed ones."""

from ..formatters.pull_request_formatter import format_pull_request_message


async def handle_pull_request_event(data: dict, context, markdown: bool = False):
    pr = data["pull_request"]
    action = data.get("action", "unknown")
    if action == "closed" and pr.get("merged"):
        action = "merged"
    return format_pull_request_message(
        action=action,
        author_name=data.get("sender", {}).get("login", "Unknown"),
        repo_name=data["repository"]["full_name"],
        pr_number=pr["number"],
        title=pr["title"],
        base_branch=pr.get("base", {}).get("ref", "unknown"),
        head_branch=pr.get("head", {}).get("ref", "unknown"),
        pr_url=pr.get("html_url", ""),
        markdown=markdown,
    )
