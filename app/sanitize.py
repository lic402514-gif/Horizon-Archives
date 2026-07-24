"""Markdown sanitization helper — strips dangerous HTML from markdown output."""
import re

_DANGEROUS = re.compile(
    r'<script[\s>]|</script>|javascript:|ona\w+\s*=|onerror\s*=|<iframe|<object|<embed|<form|data:text/html',
    re.IGNORECASE
)

def sanitize_html(html: str) -> str:
    """Remove dangerous tags/attributes while preserving markdown-generated HTML."""
    return _DANGEROUS.sub('', html)
