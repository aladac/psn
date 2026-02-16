#!/usr/bin/env python3
"""PreCompact hook stub.

Called before context compaction (when context window fills up).

Input (stdin JSON):
    - context_size: Current context size in tokens
    - threshold: Compaction threshold
"""
import json
import sys


def main() -> None:
    """Process PreCompact hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: no action
    # Future: save important context to memory before compaction
    pass


if __name__ == "__main__":
    main()
