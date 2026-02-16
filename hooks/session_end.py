#!/usr/bin/env python3
"""SessionEnd hook stub.

Called when a Claude Code session ends.

Input (stdin JSON):
    - session_id: Unique session identifier
    - duration: How long the session lasted
    - timestamp: Session end time
"""
import json
import sys


def main() -> None:
    """Process SessionEnd hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: no action
    # Future: save session state, persist memory
    pass


if __name__ == "__main__":
    main()
