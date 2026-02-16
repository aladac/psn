#!/usr/bin/env python3
"""PostToolUse hook stub.

Called after a tool has executed. Can process results or trigger side effects.

Input (stdin JSON):
    - tool_name: Name of the tool that was called
    - tool_input: Parameters that were passed
    - tool_output: Result from the tool
    - error: Optional error if tool failed
"""
import json
import sys


def main() -> None:
    """Process PostToolUse hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: no action
    pass


if __name__ == "__main__":
    main()
