#!/usr/bin/env python3
"""PreToolUse hook stub.

Called before a tool is executed. Can block or modify tool calls.

Input (stdin JSON):
    - tool_name: Name of the tool being called
    - tool_input: Parameters being passed to the tool

Output (stdout JSON):
    - decision: "allow" | "block" | "modify"
    - reason: Optional explanation
    - modified_input: If decision is "modify", the new input
"""
import json
import sys


def main() -> None:
    """Process PreToolUse hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: allow all tool calls
    result = {"decision": "allow"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
