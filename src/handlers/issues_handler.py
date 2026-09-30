"""Extract issue details."""

from ..formatters.issues_formatter import format_issue_message


async def handle_issues_event(data: dict, context, markdown: bool = False):
    issue = data["issue"]
    return format_issue_message(
        action=data.get("action", "unknown"),
        author_name=data.get("sender", {}).get("login", "Unknown"),
        repo_name=data["repository"]["full_name"],
        issue_number=issue["number"],
        title=issue["title"],
        issue_url=issue.get("html_url", ""),
        markdown=markdown,
    )
