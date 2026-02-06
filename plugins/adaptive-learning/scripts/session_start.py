#!/usr/bin/env python3
"""
SessionStart hook: load learned instincts into context.

Scans instinct directories, applies confidence decay, and prints
a summary of active instincts. Stays silent if none qualify.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import get_config, get_storage_dir, parse_frontmatter


def load_instincts(storage, cfg):
    """Scan personal + inherited instinct dirs, return qualifying instincts."""
    min_conf = cfg.get("session_start", {}).get("min_confidence", 0.3)
    weekly_decay = cfg.get("confidence", {}).get("weekly_decay", 0.02)
    now = datetime.now(timezone.utc)
    instincts = []

    for subdir in ("instincts/personal", "instincts/inherited"):
        d = storage / subdir
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            meta, body = parse_frontmatter(text)
            if not meta.get("id"):
                continue

            # Apply confidence decay since last_confirmed
            confidence = meta.get("confidence", 0.3)
            last = meta.get("last_confirmed", "")
            if last:
                try:
                    last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                    weeks_elapsed = (now - last_dt).days / 7.0
                    confidence -= weekly_decay * weeks_elapsed
                except (ValueError, TypeError):
                    pass

            confidence = max(0.0, min(1.0, confidence))
            if confidence < min_conf:
                continue

            instincts.append({
                "id": meta["id"],
                "confidence": round(confidence, 2),
                "trigger": meta.get("trigger", ""),
                "domain": meta.get("domain", "general"),
                "source": "inherited" if "inherited" in str(f) else "personal",
                "body": body.strip(),
            })

    instincts.sort(key=lambda x: x["confidence"], reverse=True)
    return instincts


def format_summary(instincts, max_display):
    """Format instincts as a concise context block."""
    shown = instincts[:max_display]
    lines = [f"[AdaptiveLearning] {len(instincts)} active instinct(s):"]

    for inst in shown:
        bar_len = int(inst["confidence"] * 10)
        bar = "#" * bar_len + "." * (10 - bar_len)
        tag = f"[{inst['source'][0].upper()}]"  # [P]ersonal or [I]nherited
        lines.append(f"  {tag} [{bar}] {inst['id']}: {inst['trigger']}")

    if len(instincts) > max_display:
        lines.append(f"  ... and {len(instincts) - max_display} more (use /adaptive-learning:status)")

    return "\n".join(lines)


def main():
    cfg = get_config()
    storage = get_storage_dir()
    instincts = load_instincts(storage, cfg)

    if not instincts:
        return

    max_display = cfg.get("session_start", {}).get("max_instincts", 5)
    print(format_summary(instincts, max_display))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # Never block the session
    sys.exit(0)
