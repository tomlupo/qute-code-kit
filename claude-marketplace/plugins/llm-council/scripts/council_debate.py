#!/usr/bin/env python3
"""
Council Debate Command Handler

Executes the /council:debate command for structured debates.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from council_engine import CouncilEngine, CouncilResult


class DebateEngine:
    """Extended council engine for multi-round debates."""

    def __init__(self):
        self.engine = CouncilEngine()

    async def run_debate(
        self,
        topic: str,
        rounds: int = 2,
        positions: Optional[list[str]] = None
    ) -> str:
        """Execute full debate workflow."""
        models = self.engine.get_enabled_models()

        if len(models) < 2:
            raise ValueError("Debate requires at least 2 enabled models")

        # Assign positions if specified
        position_assignments = {}
        if positions and len(positions) >= len(models):
            for i, model in enumerate(models):
                position_assignments[model["name"]] = positions[i]

        # Round 1: Opening statements
        opening_prompt = self._build_opening_prompt(topic, position_assignments)
        opening_responses = await self.engine.run_stage_1(
            opening_prompt,
            "You are participating in a structured debate. Present your position clearly with evidence."
        )

        # Build debate history
        debate_history = self._format_responses_for_context(opening_responses)

        # Rebuttal rounds
        rebuttal_responses = []
        for round_num in range(rounds - 1):
            rebuttal_prompt = self._build_rebuttal_prompt(
                topic, debate_history, round_num + 1
            )
            round_responses = await self.engine.run_stage_1(
                rebuttal_prompt,
                "You are in the rebuttal phase. Address counterarguments and strengthen your position."
            )
            rebuttal_responses.append(round_responses)
            debate_history += "\n\n" + self._format_responses_for_context(round_responses)

        # Peer evaluation of final positions
        all_responses = opening_responses + [r for batch in rebuttal_responses for r in batch]
        peer_reviews, mapping = await self.engine.run_stage_2(
            topic, opening_responses, models
        )

        # Chairman verdict
        chairman = self.engine.select_chairman(models)
        verdict = await self._get_chairman_verdict(
            topic, opening_responses, rebuttal_responses, peer_reviews, mapping, chairman
        )

        return self._format_debate_output(
            topic, opening_responses, rebuttal_responses,
            peer_reviews, mapping, verdict, chairman["name"]
        )

    def _build_opening_prompt(
        self,
        topic: str,
        position_assignments: dict[str, str]
    ) -> str:
        """Build opening statement prompt."""
        base_prompt = f"""You are participating in a structured debate on the following topic:

## Topic
{topic}

## Your Task
Present your opening statement:
1. **State your position** clearly (pro, con, or nuanced view)
2. **Provide 3-4 key arguments** supporting your position
3. **Include evidence or examples** for each argument
4. **Anticipate counterarguments** briefly

Keep your response focused and persuasive. You do not know what positions other debaters will take.
"""
        return base_prompt

    def _build_rebuttal_prompt(
        self,
        topic: str,
        debate_history: str,
        round_num: int
    ) -> str:
        """Build rebuttal round prompt."""
        return f"""## Debate Topic
{topic}

## Previous Arguments (Anonymized)
{debate_history}

## Rebuttal Round {round_num}

Now respond to the other positions:
1. **Address the strongest counterarguments** to your position
2. **Point out weaknesses** in opposing arguments
3. **Strengthen your case** with additional evidence
4. **Find common ground** where possible

Be respectful but incisive. Focus on the arguments, not the debaters.
"""

    def _format_responses_for_context(self, responses) -> str:
        """Format responses for inclusion in subsequent prompts."""
        lines = []
        for i, resp in enumerate(responses):
            if not resp.error:
                anon_id = f"Debater {chr(65 + i)}"
                lines.append(f"### {anon_id}")
                lines.append(resp.response)
                lines.append("")
        return "\n".join(lines)

    async def _get_chairman_verdict(
        self,
        topic: str,
        opening: list,
        rebuttals: list[list],
        reviews: list,
        mapping: dict,
        chairman: dict
    ) -> str:
        """Get chairman's verdict on the debate."""
        # Format all arguments
        all_arguments = "## Opening Statements\n"
        for resp in opening:
            if not resp.error:
                all_arguments += f"\n### {resp.model_name}\n{resp.response}\n"

        for i, round_responses in enumerate(rebuttals):
            all_arguments += f"\n## Rebuttal Round {i + 1}\n"
            for resp in round_responses:
                if not resp.error:
                    all_arguments += f"\n### {resp.model_name}\n{resp.response}\n"

        verdict_prompt = f"""You are the Chairman of this debate. Review all arguments and provide your verdict.

## Topic
{topic}

{all_arguments}

## Your Verdict

Provide:
1. **Strongest Arguments Per Position**: What were the best points on each side?
2. **Areas of Agreement**: What did all debaters agree on?
3. **Key Disagreements**: Where did they fundamentally differ?
4. **Your Verdict**: Based on argument quality, which position is most defensible? Why?

Be balanced but decisive. It's okay to declare a winner if one position was clearly stronger.
"""

        response = await self.engine.call_model(
            chairman, verdict_prompt,
            "You are a fair and analytical debate judge."
        )
        return response.response if not response.error else "Verdict generation failed."

    def _format_debate_output(
        self,
        topic: str,
        opening: list,
        rebuttals: list[list],
        reviews: list,
        mapping: dict,
        verdict: str,
        chairman_name: str
    ) -> str:
        """Format complete debate output."""
        lines = [
            "🏛️ Council Debate",
            "━━━━━━━━━━━━━━━",
            f"Topic: \"{topic}\"",
            "",
            "## Opening Statements",
            ""
        ]

        for resp in opening:
            if resp.error:
                lines.append(f"### {resp.model_name} (ERROR)")
                lines.append(f"*{resp.error}*")
            else:
                lines.append(f"### {resp.model_name}")
                lines.append(resp.response)
            lines.append("")

        for i, round_responses in enumerate(rebuttals):
            lines.append(f"## Rebuttal Round {i + 1}")
            lines.append("")
            for resp in round_responses:
                if not resp.error:
                    lines.append(f"### {resp.model_name}")
                    lines.append(resp.response)
                    lines.append("")

        if reviews:
            lines.append("## Peer Evaluation")
            lines.append("")
            lines.append("| Debater | Reviewer | Score |")
            lines.append("|---------|----------|-------|")
            for review in reviews:
                model_name = mapping.get(review.reviewed_anonymous_id, "?")
                lines.append(
                    f"| {review.reviewed_anonymous_id} ({model_name}) | "
                    f"{review.reviewer_model} | {review.total_score} |"
                )
            lines.append("")

        lines.append(f"## Chairman Verdict ({chairman_name})")
        lines.append("")
        lines.append(verdict)

        return "\n".join(lines)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run a council debate")
    parser.add_argument("topic", nargs="?", help="The debate topic")
    parser.add_argument("--rounds", type=int, default=2, help="Number of rounds")
    parser.add_argument("--positions", type=str, help="Comma-separated positions")
    return parser.parse_args()


def main():
    args = parse_args()

    topic = args.topic
    if not topic and not sys.stdin.isatty():
        topic = sys.stdin.read().strip()

    if not topic:
        print("Error: No topic provided")
        print("Usage: council_debate.py \"<topic>\" [--rounds N] [--positions a,b,c]")
        sys.exit(1)

    positions = args.positions.split(",") if args.positions else None

    try:
        debate = DebateEngine()
        output = asyncio.run(debate.run_debate(
            topic=topic,
            rounds=args.rounds,
            positions=positions
        ))
        print(output)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Debate failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
