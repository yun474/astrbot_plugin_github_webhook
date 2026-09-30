"""Verify Markdown escaping and event details."""

from src.formatters.markdown import escape_text, link
from src.handlers.issues_handler import handle_issues_event
from src.handlers.pull_request_handler import handle_pull_request_event
from src.handlers.push_handler import handle_push_event
from tests.test_webhook import PUSH


def test_untrusted_title_cannot_inject_link_or_heading():
    assert (
        escape_text("[click](bad)\n# title *bold*")
        == r"\[click\]\(bad\) \# title \*bold\*"
    )
    assert link("title", "javascript:alert(1)") == "title"
    assert "%29" in link("title", "https://example.com/x)bad")


async def test_push_lists_multiple_commits_and_limits_length():
    data = dict(PUSH, commits=PUSH["commits"] * 10)
    text = await handle_push_event(data, None, markdown=True)
    assert "20 条" in text
    assert text.count("- [") == 5
    assert "另有 15 条提交未展开" in text


async def test_issue_title_is_escaped():
    text = await handle_issues_event(
        {
            "repository": {"full_name": "owner/repo"},
            "action": "opened",
            "issue": {
                "number": 3,
                "title": "[x](bad)",
                "html_url": "https://github.com/o/r/issues/3",
            },
        },
        None,
        markdown=True,
    )
    assert r"\[x\]\(bad\)" in text


async def test_merged_pr_is_not_reported_as_closed():
    text = await handle_pull_request_event(
        {
            "repository": {"full_name": "owner/repo"},
            "action": "closed",
            "pull_request": {"number": 1, "title": "fix", "merged": True},
        },
        None,
        markdown=True,
    )
    assert "已合并" in text
    assert "关闭" not in text
