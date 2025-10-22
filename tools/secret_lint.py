#!/usr/bin/env python3
from __future__ import annotations
import math, re
from typing import Iterable, List, Dict, Any

_DEFAULT_PATTERNS: List[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("aws_secret_access_key", re.compile(r"(?i)aws(.{0,20})?(secret|sk)[^\S\r\n]*[:=][^\S\r\n]*([A-Za-z0-9/+=]{40})")),
    ("generic_token", re.compile(r"(?i)(token|api[_-]?key|secret)[^\S\r\n]*[:=][^\S\r\n]*([A-Za-z0-9_\-]{16,})")),
    ("private_key_block", re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----")),
]

def detect_patterns(text: str, extra_patterns: Iterable[tuple[str, str]] | None = None) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    patterns = list(_DEFAULT_PATTERNS)
    if extra_patterns:
        patterns.extend([(name, re.compile(rx)) for name, rx in extra_patterns])
    for name, rx in patterns:
        for m in rx.finditer(text or ""):
            results.append({"rule": name, "match": m.group(0), "span": [m.start(), m.end()]})
    return results

def check_entropy(s: str, threshold: float = 4.0) -> bool:
    if not s:
        return False
    import collections
    freq = collections.Counter(s)
    n = len(s)
    H = -sum((c / n) * math.log2(c / n) for c in freq.values())
    return H >= threshold

def scan_for_secrets(text: str) -> List[Dict[str, Any]]:
    findings = detect_patterns(text)
    for token in re.findall(r"[A-Za-z0-9/_+=-]{20,}", text or ""):
        if check_entropy(token):
            findings.append({"rule": "high_entropy_token", "match": token, "span": [-1, -1]})
    return findings