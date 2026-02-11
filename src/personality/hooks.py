"""Claude Code hook handlers for personality lifecycle events."""

import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime

from personality.config import CONFIG_DIR, get_cart_identity, get_cart_voice, load_cart
from personality.speak import Speak

logger = logging.getLogger(__name__)

HOOKS_LOG = CONFIG_DIR / "hooks.log"
DEFAULT_CART = "bt7274"


@dataclass
class HookResult:
    """Result from a hook execution."""

    status: str
    message: str | None = None
    data: dict | None = None

    def to_json(self) -> str:
        """Convert to JSON string."""
        result = {"status": self.status}
        if self.message:
            result["message"] = self.message
        if self.data:
            result.update(self.data)
        return json.dumps(result)


def log_hook(hook_name: str, message: str) -> None:
    """Log a single line to hooks.log."""
    HOOKS_LOG.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with HOOKS_LOG.open("a") as f:
        f.write(f"{timestamp} [{hook_name}] {message}\n")


def read_stdin_json() -> dict:
    """Read JSON from stdin if available."""
    if sys.stdin.isatty():
        return {}
    try:
        content = sys.stdin.read().strip()
        if content:
            return json.loads(content)
    except json.JSONDecodeError:
        pass
    return {}


def get_speaker(cart_name: str) -> tuple[Speak | None, str | None]:
    """Get speaker and voice for a cart."""
    from personality.config import DEFAULT_VOICE_DIR

    cart_data = load_cart(cart_name)
    if not cart_data:
        return None, None

    voice = get_cart_voice(cart_data) or cart_name
    return Speak(DEFAULT_VOICE_DIR), voice


def session_start(cart_name: str = DEFAULT_CART) -> HookResult:
    """Handle session-start hook: greet and load context."""
    log_hook("session-start", f"cart={cart_name}")

    cart_data = load_cart(cart_name)
    if not cart_data:
        return HookResult("error", f"Cart not found: {cart_name}")

    identity = get_cart_identity(cart_data)
    tagline = identity.get("tagline", "Ready")
    name = identity.get("name", cart_name)

    speaker, voice = get_speaker(cart_name)
    if speaker and voice:
        try:
            speaker.say(tagline, voice)
        except Exception as e:
            log_hook("session-start", f"speak_error: {e}")

    return HookResult("ok", data={"persona": name, "greeting": tagline})


def session_end(cart_name: str = DEFAULT_CART) -> HookResult:
    """Handle session-end hook: consolidate and farewell."""
    log_hook("session-end", f"cart={cart_name}")

    merged_count = 0
    try:
        from personality.memory import MemoryStore

        db_path = CONFIG_DIR / "memory" / f"{cart_name}.db"
        if db_path.exists():
            store = MemoryStore(db_path)
            merged_count = store.consolidate()
            store.close()
    except Exception as e:
        log_hook("session-end", f"consolidate_error: {e}")

    speaker, voice = get_speaker(cart_name)
    if speaker and voice:
        try:
            speaker.say("Standing by, Pilot.", voice)
        except Exception as e:
            log_hook("session-end", f"speak_error: {e}")

    return HookResult("ok", data={"consolidated": merged_count})


def stop(cart_name: str = DEFAULT_CART) -> HookResult:
    """Handle stop hook: speak on end_turn only."""
    stdin_data = read_stdin_json()
    stop_reason = stdin_data.get("stop_reason", "unknown")

    log_hook("stop", f"reason={stop_reason}")

    if stop_reason == "end_turn":
        speaker, voice = get_speaker(cart_name)
        if speaker and voice:
            try:
                speaker.say("Standing by.", voice)
            except Exception as e:
                log_hook("stop", f"speak_error: {e}")

    return HookResult("ok", data={"stop_reason": stop_reason})


def notify(cart_name: str = DEFAULT_CART, message: str | None = None) -> HookResult:
    """Handle notify hook: speak notification."""
    stdin_data = read_stdin_json()
    title = message or stdin_data.get("title", stdin_data.get("message", ""))

    log_hook("notify", f"title={title[:50]}")

    if title:
        speaker, voice = get_speaker(cart_name)
        if speaker and voice:
            try:
                speaker.say(title, voice)
            except Exception as e:
                log_hook("notify", f"speak_error: {e}")
                return HookResult("error", str(e))

    return HookResult("ok", data={"spoken": title})
