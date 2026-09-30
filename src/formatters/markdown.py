"""Escape event text and links before placing them in a Markdown notification."""

import re
from urllib.parse import quote, urlsplit


def escape_text(value: str) -> str:
    text = " ".join(str(value or "").split())
    return re.sub(r"([\\\x60*_{}\[\]()#+\-.!|>~<])", r"\\\1", text)


def link(label: str, url: str) -> str:
    label = escape_text(label)
    parsed = urlsplit(url or "")
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        return label
    return f"[{label}]({quote(url, safe=':/?&=#%+@,;~-._')})"
