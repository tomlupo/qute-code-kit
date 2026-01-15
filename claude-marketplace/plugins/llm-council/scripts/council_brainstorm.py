#!/usr/bin/env python3
"""
Council Brainstorm Command Handler

Executes the /council:brainstorm command for collaborative idea generation.
"""

import asyncio
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from council_engine import CouncilEngine


class BrainstormEngine:
    """Extended council engine for collaborative brainstorming."""

    STYLES = {
        "wild": {
            "description": "creative and unconventional",
            "prompt_modifier": "Be creative and unconventional. No idea is too wild. Think outside the box.",
            "idea_count": 7
        },
        "practical": {
            "description": "feasible and implementable",
            "prompt_modifier": "Focus on practical, implementable ideas. Consider feasibility and resources.",
            "idea_count": 5
        },
        "balanced": {
            "description": "mix of creative and practical",
            "prompt_modifier": "Balance creativity with practicality. Include both innovative and achievable ideas.",
            "idea_count": 5
        }
    }

    def __init__(self):
        self.engine = CouncilEngine()

    async def run_brainstorm(
        self,
        topic: str,
        rounds: int = 2,
        style: str = "balanced"
    ) -> str:
        """Execute brainstorming workflow."""
        models = self.engine.get_enabled_models()

        if len(models) < 2:
            raise ValueError("Brainstorming requires at least 2 enabled models")

        style_config = self.STYLES.get(style, self.STYLES["balanced"])

        # Round 1: Independent idea generation
        round1_prompt = self._build_round1_prompt(topic, style_config)
        round1_responses = await self.engine.run_stage_1(
            round1_prompt,
            f"You are brainstorming. {style_config['prompt_modifier']}"
        )

        # Parse round 1 ideas
        all_ideas = {}
        for resp in round1_responses:
            if not resp.error:
                ideas = self._parse_ideas(resp.response)
                all_ideas[resp.model_name] = ideas

        # Additional rounds: Cross-pollination
        cross_pollination = []
        for round_num in range(1, rounds):
            round_prompt = self._build_cross_pollination_prompt(
                topic, all_ideas, style_config, round_num
            )
            round_responses = await self.engine.run_stage_1(
                round_prompt,
                "Build on others' ideas. Combine, improve, and generate new variations."
            )

            round_ideas = {}
            for resp in round_responses:
                if not resp.error:
                    ideas = self._parse_ideas(resp.response)
                    round_ideas[resp.model_name] = ideas

            cross_pollination.append(round_ideas)

        # Chairman synthesis
        chairman = self.engine.select_chairman(models)
        synthesis = await self._get_chairman_synthesis(
            topic, all_ideas, cross_pollination, style_config, chairman
        )

        return self._format_brainstorm_output(
            topic, style, all_ideas, cross_pollination,
            synthesis, chairman["name"]
        )

    def _build_round1_prompt(self, topic: str, style_config: dict) -> str:
        """Build initial brainstorming prompt."""
        idea_count = style_config["idea_count"]

        return f"""## Brainstorming Topic
{topic}

## Your Task
Generate {idea_count}-10 ideas related to this topic.

Guidelines:
- {style_config['prompt_modifier']}
- Don't filter yourself - include all ideas that come to mind
- Brief description for each (1-2 sentences)
- Number your ideas

Format:
1. **[Idea Title]**: Brief description
2. **[Idea Title]**: Brief description
...
"""

    def _build_cross_pollination_prompt(
        self,
        topic: str,
        all_ideas: dict[str, list],
        style_config: dict,
        round_num: int
    ) -> str:
        """Build cross-pollination prompt."""
        # Format others' ideas (anonymized)
        ideas_text = ""
        for i, (model, ideas) in enumerate(all_ideas.items()):
            ideas_text += f"\n### Participant {chr(65 + i)}\n"
            for j, idea in enumerate(ideas[:5], 1):
                ideas_text += f"{j}. {idea}\n"

        return f"""## Brainstorming Topic
{topic}

## Ideas from Other Participants
{ideas_text}

## Round {round_num + 1}: Cross-Pollination

Now that you've seen others' ideas:
1. **Build on** 1-2 promising ideas from others
2. **Combine** ideas from different participants
3. **Generate** 2-3 new variations or improvements

Format each as:
- **[Idea Title]** (builds on Participant X's idea #Y): Description
- **[Combined Idea]** (combines X#1 + Y#2): Description
- **[New Variation]**: Description
"""

    def _parse_ideas(self, response: str) -> list[str]:
        """Parse ideas from response."""
        ideas = []
        lines = response.split("\n")

        for line in lines:
            line = line.strip()
            # Match numbered ideas or bullet points
            match = re.match(r'^[\d\-\*\•]+[\.\)]\s*(.+)', line)
            if match:
                idea = match.group(1).strip()
                if idea and len(idea) > 10:  # Filter out very short lines
                    ideas.append(idea)

        return ideas

    async def _get_chairman_synthesis(
        self,
        topic: str,
        round1_ideas: dict[str, list],
        cross_pollination: list[dict],
        style_config: dict,
        chairman: dict
    ) -> str:
        """Get chairman's synthesis of all ideas."""
        # Compile all ideas
        all_ideas_text = "## Round 1 Ideas\n"
        for model, ideas in round1_ideas.items():
            all_ideas_text += f"\n### {model}\n"
            for i, idea in enumerate(ideas, 1):
                all_ideas_text += f"{i}. {idea}\n"

        for round_num, round_ideas in enumerate(cross_pollination, 2):
            all_ideas_text += f"\n## Round {round_num} Ideas\n"
            for model, ideas in round_ideas.items():
                all_ideas_text += f"\n### {model}\n"
                for i, idea in enumerate(ideas, 1):
                    all_ideas_text += f"{i}. {idea}\n"

        synthesis_prompt = f"""You are synthesizing a brainstorming session.

## Topic
{topic}

{all_ideas_text}

## Your Task

Create a synthesized output:

1. **Cluster Ideas**: Group related ideas into 3-5 themes

2. **Top Ideas by Category**:
   - High-Impact, Low-Effort (quick wins)
   - High-Impact, Medium-Effort (major initiatives)
   - Innovative/Long-term (future possibilities)

3. **Best Combinations**: Highlight the best hybrid ideas that emerged

4. **Recommended Next Steps**: What should be done first?

Be concise but comprehensive. Prioritize quality over quantity.
"""

        response = await self.engine.call_model(
            chairman, synthesis_prompt,
            "You are synthesizing brainstorming results into actionable insights."
        )
        return response.response if not response.error else "Synthesis failed."

    def _format_brainstorm_output(
        self,
        topic: str,
        style: str,
        round1_ideas: dict[str, list],
        cross_pollination: list[dict],
        synthesis: str,
        chairman_name: str
    ) -> str:
        """Format complete brainstorm output."""
        lines = [
            "🏛️ Council Brainstorm",
            "━━━━━━━━━━━━━━━━━━━",
            f"Topic: \"{topic}\"",
            f"Style: {style.title()}",
            "",
            "## Round 1: Initial Ideas",
            ""
        ]

        # Round 1 ideas
        for model, ideas in round1_ideas.items():
            lines.append(f"### {model} ({len(ideas)} ideas)")
            for i, idea in enumerate(ideas, 1):
                # Truncate long ideas
                display_idea = idea if len(idea) < 100 else idea[:97] + "..."
                lines.append(f"{i}. {display_idea}")
            lines.append("")

        # Cross-pollination rounds
        for round_num, round_ideas in enumerate(cross_pollination, 2):
            lines.append(f"## Round {round_num}: Cross-Pollination")
            lines.append("")
            for model, ideas in round_ideas.items():
                lines.append(f"### {model}")
                for idea in ideas:
                    display_idea = idea if len(idea) < 100 else idea[:97] + "..."
                    lines.append(f"- {display_idea}")
                lines.append("")

        # Chairman synthesis
        lines.append(f"## Synthesized Ideas (Chairman: {chairman_name})")
        lines.append("")
        lines.append(synthesis)

        return "\n".join(lines)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Brainstorm with the council")
    parser.add_argument("topic", nargs="?", help="The brainstorming topic")
    parser.add_argument("--rounds", type=int, default=2, help="Number of rounds")
    parser.add_argument("--style", type=str, default="balanced",
                        choices=["wild", "practical", "balanced"],
                        help="Brainstorming style")
    return parser.parse_args()


def main():
    args = parse_args()

    topic = args.topic
    if not topic and not sys.stdin.isatty():
        topic = sys.stdin.read().strip()

    if not topic:
        print("Error: No topic provided")
        print('Usage: council_brainstorm.py "<topic>" [--rounds N] [--style wild|practical|balanced]')
        sys.exit(1)

    try:
        engine = BrainstormEngine()
        output = asyncio.run(engine.run_brainstorm(
            topic=topic,
            rounds=args.rounds,
            style=args.style
        ))
        print(output)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Brainstorm failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
