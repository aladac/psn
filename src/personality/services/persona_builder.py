"""
Persona builder service for constructing character instructions.

Builds LLM instruction prompts from persona memories for use in
session start hooks and persona display.
"""

from datetime import datetime

from personality.schemas.pcart import Cartridge
from personality.schemas.training import TrainingMemory

# Category display titles for persona sections
CATEGORY_TITLES = {
    "identity": "Identity",
    "trait": "Personality Traits",
    "belief": "Beliefs & Values",
    "speech": "Speech Patterns",
    "knowledge": "Knowledge",
    "relationship": "Relationships",
    "behavior": "Behaviors",
    "emotion": "Emotional Tendencies",
    "goal": "Goals & Motivations",
    "memory": "Background & Memories",
    "quirk": "Quirks & Mannerisms",
    "protocol": "Protocols",
    "capability": "Capabilities",
    "logic": "Logic & Reasoning",
    "quote": "Iconic Quotes",
}

# Persona-related subject prefixes
PERSONA_PREFIXES = ("self.", "identity.", "user.", "meta.")


class PersonaBuilder:
    """
    Builds persona/character instructions from cartridge memories.

    Provides consistent formatting of identity memories into
    roleplay instructions for the LLM.
    """

    @staticmethod
    def build_instructions(cart: Cartridge) -> str:
        """
        Build persona instructions from a loaded cartridge.

        Groups memories by subject category and formats them
        as natural language instructions for the LLM.

        Args:
            cart: Loaded Cartridge with persona and preferences.

        Returns:
            Formatted persona instructions string.
        """
        memories = cart.persona.memories
        if not memories:
            return ""

        # Group memories by top-level subject
        groups: dict[str, list[TrainingMemory]] = {}
        for mem in memories:
            parts = mem.subject.split(".")
            category = parts[0] if parts else "other"

            if category not in groups:
                groups[category] = []
            groups[category].append(mem)

        lines = ["## Your Character\n\n"]

        # Add identity header from preferences if available
        identity = cart.preferences.identity
        if identity.name:
            lines.append(f"You are **{identity.name}**")
            if identity.type:
                lines.append(f", a {identity.type}")
            lines.append(".\n\n")
        elif cart.tag:
            lines.append(f"You are roleplaying as **{cart.tag}**.\n\n")

        if identity.tagline:
            lines.append(f'> "{identity.tagline}"\n\n')

        lines.append("Stay in character at all times. Use the personality traits, ")
        lines.append("speech patterns, and knowledge provided below.\n")

        # Format self.* memories (traits, beliefs, speech patterns, etc.)
        if "self" in groups:
            lines.extend(PersonaBuilder._format_self_memories(groups["self"]))
            del groups["self"]

        # Format user.* memories (how to address user, etc.)
        if "user" in groups:
            lines.append("\n### User Interaction\n\n")
            for mem in groups["user"]:
                lines.append(f"- {mem.content}\n")
            del groups["user"]

        # Format meta if present
        if "meta" in groups:
            lines.append("\n### Meta Information\n\n")
            for mem in groups["meta"]:
                lines.append(f"- {mem.content}\n")
            del groups["meta"]

        # Format any remaining groups (except identity which is in header)
        if "identity" in groups:
            del groups["identity"]

        for category, mems in sorted(groups.items()):
            title = CATEGORY_TITLES.get(category, category.title())
            lines.append(f"\n### {title}\n\n")
            for mem in mems:
                lines.append(f"- {mem.content}\n")

        return "".join(lines)

    @staticmethod
    def _format_self_memories(memories: list[TrainingMemory]) -> list[str]:
        """
        Format self.* memories grouped by sub-category.

        Args:
            memories: List of self.* memories.

        Returns:
            List of formatted lines.
        """
        lines: list[str] = []

        # Sub-group by second level (trait, belief, speech, etc.)
        self_groups: dict[str, list[TrainingMemory]] = {}
        for mem in memories:
            parts = mem.subject.split(".")
            sub_category = parts[1] if len(parts) > 1 else "general"
            if sub_category not in self_groups:
                self_groups[sub_category] = []
            self_groups[sub_category].append(mem)

        # Define preferred order for sections
        order = [
            "identity",
            "trait",
            "protocol",
            "speech",
            "capability",
            "relationship",
            "quote",
            "logic",
            "belief",
            "behavior",
            "emotion",
            "goal",
            "memory",
            "quirk",
            "knowledge",
        ]

        # Format each sub-category in order
        seen = set()
        for sub_cat in order:
            if sub_cat in self_groups:
                title = CATEGORY_TITLES.get(sub_cat, sub_cat.title())
                lines.append(f"\n### {title}\n\n")
                for mem in self_groups[sub_cat]:
                    lines.append(f"- {mem.content}\n")
                seen.add(sub_cat)

        # Format any remaining sub-categories
        for sub_cat, mems in sorted(self_groups.items()):
            if sub_cat not in seen:
                title = CATEGORY_TITLES.get(sub_cat, sub_cat.title())
                lines.append(f"\n### {title}\n\n")
                for mem in mems:
                    lines.append(f"- {mem.content}\n")

        return lines

    @staticmethod
    def build_greeting(cart: Cartridge, user_name: str | None = None) -> str:
        """
        Build a greeting message using persona's greeting template.

        Replaces placeholders:
        - {{USER_ID}} or {{user}} -> user_name or "Pilot"
        - {{TIME_GREETING}} -> "Good morning/afternoon/evening"

        Args:
            cart: Loaded Cartridge.
            user_name: User's name for personalization.

        Returns:
            Greeting message.
        """
        # Find greeting in memories
        greeting_template = None
        for mem in cart.persona.memories:
            if "greeting" in mem.subject.lower() or "salutation" in mem.subject.lower():
                greeting_template = mem.content
                break

        if not greeting_template:
            # Default greeting based on identity
            name = cart.preferences.identity.name or cart.tag
            return f"Hello, I am {name}."

        # Replace placeholders
        greeting = greeting_template
        greeting = greeting.replace("{{USER_ID}}", user_name or "User")
        greeting = greeting.replace("{{user}}", user_name or "User")
        greeting = greeting.replace("{{TIME_GREETING}}", _get_time_greeting())

        return greeting

    @staticmethod
    def build_summary(cart: Cartridge) -> str:
        """
        Build a brief persona summary for display.

        Args:
            cart: Loaded Cartridge.

        Returns:
            Brief summary string.
        """
        identity = cart.preferences.identity

        parts = []
        if identity.name:
            parts.append(identity.name)
        elif cart.tag:
            parts.append(cart.tag)

        if identity.type:
            parts.append(f"({identity.type})")

        if cart.manifest.version:
            parts.append(f"v{cart.manifest.version}")

        return " ".join(parts) if parts else "Persona loaded"


def _get_time_greeting() -> str:
    """Get time-appropriate greeting."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"
