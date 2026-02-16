#!/usr/bin/env python3
"""Stop hook stub.

Called when the main agent stops (completes or is interrupted).

Input (stdin JSON):
    - reason: Why the agent stopped
    - stop_message: Final message if any
"""
import json
import sys


def main() -> None:
    """Process Stop hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: no action
    pass


if __name__ == "__main__":
    main()
