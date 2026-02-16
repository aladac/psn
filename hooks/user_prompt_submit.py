#!/usr/bin/env python3
"""UserPromptSubmit hook stub.

Called when the user submits a prompt. Can modify or block the prompt.

Input (stdin JSON):
    - prompt: The user's input text
    - timestamp: When submitted

Output (stdout JSON):
    - decision: "allow" | "block" | "modify"
    - modified_prompt: If decision is "modify", the new prompt
    - message: Optional message to show user
"""
import json
import sys


def main() -> None:
    """Process UserPromptSubmit hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: allow all prompts
    result = {"decision": "allow"}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
