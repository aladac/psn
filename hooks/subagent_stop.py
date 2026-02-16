#!/usr/bin/env python3
"""SubagentStop hook stub.

Called when a subagent (Task tool) completes.

Input (stdin JSON):
    - agent_type: Type of subagent that ran
    - task_description: What the agent was asked to do
    - result: Agent's output
"""
import json
import sys


def main() -> None:
    """Process SubagentStop hook."""
    _input_data = json.loads(sys.stdin.read())

    # Stub: no action
    pass


if __name__ == "__main__":
    main()
