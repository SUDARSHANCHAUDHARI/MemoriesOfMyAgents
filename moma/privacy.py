"""
Privacy filter — strips secrets from observation text before writing.
Patterns: API keys, tokens, passwords, connection strings.
"""
import re

_PATTERNS = [
    # Generic: key=value where value looks like a secret
    (r'(?i)(api[-_]?key|secret|token|password|passwd|auth|bearer)\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{16,})["\']?', r'\1=<redacted>'),
    # Anthropic / OpenAI keys
    (r'sk-[A-Za-z0-9]{20,}', '<api-key>'),
    (r'sk-ant-[A-Za-z0-9_\-]{20,}', '<api-key>'),
    # AWS
    (r'AKIA[0-9A-Z]{16}', '<aws-access-key>'),
    (r'(?i)aws.{0,20}secret.{0,20}[:=]\s*["\']?[A-Za-z0-9/+=]{40}["\']?', '<aws-secret>'),
    # GitHub / GitLab tokens
    (r'gh[pousr]_[A-Za-z0-9]{36,}', '<github-token>'),
    (r'glpat-[A-Za-z0-9_\-]{20,}', '<gitlab-token>'),
    # Generic base64-ish secrets (long random strings after = or :)
    (r'(?<=["\'])([A-Za-z0-9+/]{40,}={0,2})(?=["\'])', '<secret>'),
    # Connection strings
    (r'(?i)(mongodb|postgres|mysql|redis|amqp)://[^\s"\'<>]+', r'\1://<redacted>'),
    # Bearer tokens in headers
    (r'(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}', 'Bearer <redacted>'),
]

_COMPILED = [(re.compile(p), r) for p, r in _PATTERNS]


def scrub(text: str) -> str:
    for pattern, replacement in _COMPILED:
        text = pattern.sub(replacement, text)
    return text
