#!/usr/bin/env python3
"""
Council Ask Command Handler

Executes the /council:ask command for general questions.
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add scripts directory to path for council_engine import
sys.path.insert(0, str(Path(__file__).parent))

from council_engine import CouncilEngine


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Ask the LLM council a question")
    parser.add_argument("question", nargs="?", help="The question to ask")
    parser.add_argument("--quick", action="store_true", help="Skip peer review")
    parser.add_argument("--chairman", type=str, help="Model to use as chairman")
    return parser.parse_args()


async def run_council_ask(question: str, quick: bool = False, chairman: str = None):
    """Execute council ask workflow."""
    engine = CouncilEngine()

    # Override chairman if specified
    if chairman:
        engine.council_config["chairman_strategy"] = "fixed"
        engine.council_config["chairman_fixed_model"] = chairman

    result = await engine.execute(
        prompt=question,
        system_prompt="Answer the following question thoroughly and accurately.",
        skip_peer_review=quick
    )

    return engine.format_result(result)


def format_header(question: str, chairman: str, models: list) -> str:
    """Format the output header."""
    model_names = ", ".join([m["name"] for m in models])
    return f"""🏛️ Council Answer
━━━━━━━━━━━━━━━
Question: "{question}"
Council: {model_names} | Chairman: {chairman}
"""


def main():
    args = parse_args()

    # Get question from args or stdin
    question = args.question
    if not question and not sys.stdin.isatty():
        question = sys.stdin.read().strip()

    if not question:
        print("Error: No question provided")
        print("Usage: council_ask.py \"<question>\" [--quick] [--chairman <model>]")
        sys.exit(1)

    try:
        output = asyncio.run(run_council_ask(
            question=question,
            quick=args.quick,
            chairman=args.chairman
        ))
        print(output)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Council execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
