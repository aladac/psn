#!/usr/bin/env python3
"""Notification hook stub.

Called when Claude Code generates a notification.

Input (stdin JSON):
    - type: Notification type
    - message: Notification content
    - severity: info | warning | error
"""
import json
import sys


def main() -> None:
    """Process Notification hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: no action
    # Future: speak notifications via TTS, log to memory
    pass


if __name__ == "__main__":
    main()
