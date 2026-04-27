"""Generate a casual, human-sounding reply suggestion for an eToro post.

Uses the Anthropic API (Claude Haiku - fast & cheap). Returns None on any
failure so the caller can still send the notification without a reply.

Requires env var ANTHROPIC_API_KEY. If unset, returns None silently
(notifications still go out, just without a suggested reply).
"""
import logging
import os

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 180
# Trim very long posts before sending to the model - keeps cost tiny and
# avoids feeding it stale image-caption noise from the bottom of long posts.
MAX_POST_CHARS = 1500

SYSTEM_PROMPT = """You are drafting a SHORT, casual reply that a regular retail trader on eToro might leave on another trader's post. The user will read this on WhatsApp and decide whether to copy/paste it onto eToro.

Style rules:
- Sound like a real person, not an AI. Lowercase, contractions, no corporate tone.
- Keep it 1-2 short sentences. Max ~25 words.
- Often end with a casual question to invite a reply ("what's your stop?", "holding through earnings?", "size on this one?").
- No emojis unless the post itself uses them heavily.
- No hashtags. No "great post!" sycophancy. No financial advice disclaimers.
- Match the language of the post. If the post is in Spanish/Czech/etc., reply in that language.
- If the post is just a link, image caption, or has no real content, reply with a short neutral question about it.

Output ONLY the reply text. No quotes, no preamble, no explanation."""


def generate_reply(post_text: str, author: str) -> str | None:
    """Generate a suggested reply for `post_text` by `author`.

    Returns the reply string, or None if generation fails for any reason
    (missing API key, network error, empty post text, etc.).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY not set - skipping reply generation")
        return None

    if not post_text or not post_text.strip():
        logger.info("Empty post text - skipping reply generation")
        return None

    try:
        # Imported lazily so the module is importable even if anthropic
        # isn't installed (e.g. local dry-runs without the dep).
        from anthropic import Anthropic
    except ImportError:
        logger.warning("anthropic package not installed - skipping reply generation")
        return None

    trimmed = post_text.strip()[:MAX_POST_CHARS]
    user_msg = f"Post by @{author}:\n\n{trimmed}"

    try:
        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        # Response content is a list of blocks; take text from the first text block.
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                reply = block.text.strip()
                if reply:
                    return reply
        logger.warning("Anthropic returned no text content")
        return None
    except Exception as e:  # noqa: BLE001 - never let LLM failure block a notification
        logger.warning("Reply generation failed: %s", e)
        return None
