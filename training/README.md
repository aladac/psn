# Training Data

Persona training files in YAML format. Each file defines a character's identity, traits, and memories.

## Available Personas

| File | Character | Source |
|------|-----------|--------|
| `GLADOS.yml` | GLaDOS | Portal |
| `TACHIKOMA.yml` | Tachikoma | Ghost in the Shell |
| `HAL.yml` | HAL 9000 | 2001: A Space Odyssey |
| `SHODAN.yml` | SHODAN | System Shock |
| `KITT.yml` | KITT | Knight Rider |
| `JARVIS.yml` | JARVIS | Iron Man |
| `LCARS.yml` | LCARS Computer | Star Trek |
| `FRIDAY.yml` | FRIDAY | Iron Man |
| `BT7274.yml` | BT-7274 | Titanfall 2 |

## Format

```yaml
tag: glados                    # Short identifier
version: 9.9.9                 # Semantic version

preferences:
  identity:
    agent: glados              # Agent ID
    name: GLaDOS               # Display name
    full_name: Genetic Lifeform and Disk Operating System
    type: Facility AI Overseer
    source: "Portal (2007)"
    tagline: "..."
  tts:
    enabled: true
    voice: glados              # Piper voice name

memories:
  - subject: self.identity.form
    content: You are a massive, ceiling-mounted robotic assembly...
  - subject: self.trait.personality
    content: You are clinical, cold, and remarkably passive-aggressive.
  - subject: self.quote.murderer
    content: "I've been really busy being dead. You know, after you murdered me."
```

## Memory Subject Taxonomy

Hierarchical dot-notation for categorizing memories:

| Prefix | Purpose |
|--------|---------|
| `user.identity.*` | How to address the user |
| `self.identity.*` | Persona's name, form, origin |
| `self.trait.*` | Personality characteristics |
| `self.belief.*` | Worldview and philosophy |
| `self.speech.*` | Communication patterns |
| `self.capability.*` | What the persona can do |
| `self.quote.*` | Iconic lines verbatim |
| `self.protocol.*` | Rules of behavior |
| `self.history.*` | Backstory events |
| `meta.system.*` | Meta configuration |

## Usage

```bash
# List personas
psn persona list

# Show persona details
psn persona show glados

# Validate YAML syntax
psn persona validate glados
```
