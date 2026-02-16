#!/usr/bin/env python3
"""SessionStart hook stub.

Called when a new Claude Code session begins.

Input (stdin JSON):
    - session_id: Unique session identifier
    - working_directory: Current working directory
    - timestamp: Session start time
"""
import json
import sys


def main() -> None:
    """Process SessionStart hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: no action
    # Future: load memory context, restore session state
    pass


if __name__ == "__main__":
    main()
