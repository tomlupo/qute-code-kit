#!/usr/bin/env python3
"""
Council Decide Command Handler

Executes the /council:decide command for decision support with pros/cons.
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


class DecisionEngine:
    """Extended council engine for decision support."""

    DEFAULT_CRITERIA = ["feasibility", "cost", "complexity", "maintainability"]

    def __init__(self):
        self.engine = CouncilEngine()

    async def run_decision(
        self,
        decision: str,
        options: list[str],
        criteria: Optional[list[str]] = None
    ) -> str:
        """Execute decision support workflow."""
        models = self.engine.get_enabled_models()

        if len(models) < 2:
            raise ValueError("Decision support requires at least 2 enabled models")

        if len(options) < 2:
            raise ValueError("At least 2 options required for comparison")

        if criteria is None:
            criteria = self.DEFAULT_CRITERIA

        # Stage 1: Get individual analyses
        analysis_prompt = self._build_analysis_prompt(decision, options, criteria)
        responses = await self.engine.run_stage_1(
            analysis_prompt,
            "You are a technical analyst. Provide objective, evidence-based analysis."
        )

        # Parse analyses
        analyses = []
        for resp in responses:
            if not resp.error:
                parsed = self._parse_analysis(resp.response, options, criteria)
                parsed["model"] = resp.model_name
                analyses.append(parsed)

        # Stage 2: Peer review of analyses
        reviews, mapping = await self.engine.run_stage_2(
            f"Decision: {decision}\nOptions: {', '.join(options)}",
            responses, models
        )

        # Chairman synthesis
        chairman = self.engine.select_chairman(models)
        recommendation = await self._get_chairman_recommendation(
            decision, options, criteria, analyses, chairman
        )

        return self._format_decision_output(
            decision, options, criteria, analyses,
            reviews, mapping, recommendation, chairman["name"]
        )

    def _build_analysis_prompt(
        self,
        decision: str,
        options: list[str],
        criteria: list[str]
    ) -> str:
        """Build analysis prompt for each model."""
        options_list = "\n".join([f"- {opt}" for opt in options])
        criteria_list = "\n".join([f"- {c}" for c in criteria])

        return f"""You are evaluating options for a decision.

## Decision
{decision}

## Options to Evaluate
{options_list}

## Evaluation Criteria
{criteria_list}

## Your Task

1. **Score each option** (1-10) for each criterion

2. **List pros and cons** for each option (3-4 each)

3. **Provide your recommendation** with reasoning

Format your response as JSON:
```json
{{
  "scores": {{
    "Option1": {{"criterion1": 8, "criterion2": 7, ...}},
    "Option2": {{"criterion1": 6, "criterion2": 9, ...}}
  }},
  "pros_cons": {{
    "Option1": {{
      "pros": ["pro1", "pro2", "pro3"],
      "cons": ["con1", "con2", "con3"]
    }},
    "Option2": {{
      "pros": ["..."],
      "cons": ["..."]
    }}
  }},
  "recommendation": "Option1",
  "reasoning": "Your detailed reasoning here..."
}}
```

Be objective and thorough. Consider real-world implications.
"""

    def _parse_analysis(
        self,
        response: str,
        options: list[str],
        criteria: list[str]
    ) -> dict:
        """Parse model analysis from response."""
        try:
            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                data = json.loads(response)

            return {
                "scores": data.get("scores", {}),
                "pros_cons": data.get("pros_cons", {}),
                "recommendation": data.get("recommendation", ""),
                "reasoning": data.get("reasoning", "")
            }
        except (json.JSONDecodeError, KeyError):
            # Return empty structure if parsing fails
            return {
                "scores": {},
                "pros_cons": {},
                "recommendation": "",
                "reasoning": response[:500]  # Use raw response as reasoning
            }

    async def _get_chairman_recommendation(
        self,
        decision: str,
        options: list[str],
        criteria: list[str],
        analyses: list[dict],
        chairman: dict
    ) -> str:
        """Get chairman's final recommendation."""
        # Build summary of all analyses
        analyses_text = ""
        for analysis in analyses:
            analyses_text += f"\n### {analysis.get('model', 'Unknown')}\n"
            analyses_text += f"Recommendation: {analysis.get('recommendation', 'N/A')}\n"
            analyses_text += f"Reasoning: {analysis.get('reasoning', 'N/A')}\n"

        recommendation_prompt = f"""You are synthesizing decision analyses from multiple AI models.

## Decision
{decision}

## Options
{', '.join(options)}

## Individual Analyses
{analyses_text}

## Your Task

Provide the final recommendation:

1. **Aggregated Scores**: Average scores across all models per option
2. **Consensus Points**: What do all models agree on?
3. **Contested Points**: Where do models disagree? Resolve these.
4. **Final Recommendation**: Which option is best? With confidence level.
5. **When to Choose Differently**: Situations where other options make sense.

Be decisive but acknowledge trade-offs.
"""

        response = await self.engine.call_model(
            chairman, recommendation_prompt,
            "You are a senior technical advisor making a final recommendation."
        )
        return response.response if not response.error else "Recommendation failed."

    def _format_decision_output(
        self,
        decision: str,
        options: list[str],
        criteria: list[str],
        analyses: list[dict],
        reviews: list,
        mapping: dict,
        recommendation: str,
        chairman_name: str
    ) -> str:
        """Format complete decision output."""
        lines = [
            "🏛️ Council Decision Support",
            "━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Decision: \"{decision}\"",
            f"Options: {', '.join(options)}",
            f"Criteria: {', '.join(criteria)}",
            "",
            "## Individual Analyses",
            ""
        ]

        # Format each model's analysis
        for analysis in analyses:
            model_name = analysis.get("model", "Unknown")
            lines.append(f"### {model_name} Analysis")
            lines.append("")

            # Score table
            scores = analysis.get("scores", {})
            if scores:
                header = "| Option | " + " | ".join(criteria) + " | Total |"
                separator = "|--------|" + "|".join(["-------"] * len(criteria)) + "|-------|"
                lines.append(header)
                lines.append(separator)

                for opt in options:
                    opt_scores = scores.get(opt, {})
                    score_values = [str(opt_scores.get(c, "-")) for c in criteria]
                    total = sum(opt_scores.get(c, 0) for c in criteria)
                    lines.append(f"| {opt} | " + " | ".join(score_values) + f" | {total} |")

                lines.append("")

            # Recommendation
            rec = analysis.get("recommendation", "")
            reasoning = analysis.get("reasoning", "")
            if rec:
                lines.append(f"**Recommendation**: {rec}")
            if reasoning:
                lines.append(f"**Reasoning**: {reasoning[:200]}...")
            lines.append("")

        # Aggregated scores
        lines.append("## Aggregated Scores")
        lines.append("")
        agg_scores = self._aggregate_scores(analyses, options, criteria)

        lines.append("| Option | Avg Score | Recommendations |")
        lines.append("|--------|-----------|-----------------|")
        rec_counts = {}
        for analysis in analyses:
            rec = analysis.get("recommendation", "")
            rec_counts[rec] = rec_counts.get(rec, 0) + 1

        for opt in options:
            avg = agg_scores.get(opt, 0)
            count = rec_counts.get(opt, 0)
            lines.append(f"| {opt} | {avg:.1f} | {count}/{len(analyses)} models |")

        lines.append("")

        # Chairman recommendation
        lines.append(f"## Chairman Recommendation ({chairman_name})")
        lines.append("")
        lines.append(recommendation)

        return "\n".join(lines)

    def _aggregate_scores(
        self,
        analyses: list[dict],
        options: list[str],
        criteria: list[str]
    ) -> dict[str, float]:
        """Aggregate scores across all analyses."""
        totals = {opt: [] for opt in options}

        for analysis in analyses:
            scores = analysis.get("scores", {})
            for opt in options:
                opt_scores = scores.get(opt, {})
                total = sum(opt_scores.get(c, 0) for c in criteria)
                if total > 0:
                    totals[opt].append(total)

        return {
            opt: sum(vals) / len(vals) if vals else 0
            for opt, vals in totals.items()
        }


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Get decision support from council")
    parser.add_argument("decision", nargs="?", help="The decision to make")
    parser.add_argument("--options", type=str, required=True, help="Comma-separated options")
    parser.add_argument("--criteria", type=str, help="Comma-separated criteria")
    return parser.parse_args()


def main():
    args = parse_args()

    decision = args.decision
    if not decision and not sys.stdin.isatty():
        decision = sys.stdin.read().strip()

    if not decision:
        print("Error: No decision provided")
        print('Usage: council_decide.py "<decision>" --options "a,b,c" [--criteria "x,y,z"]')
        sys.exit(1)

    options = [o.strip() for o in args.options.split(",")]
    criteria = [c.strip() for c in args.criteria.split(",")] if args.criteria else None

    try:
        engine = DecisionEngine()
        output = asyncio.run(engine.run_decision(
            decision=decision,
            options=options,
            criteria=criteria
        ))
        print(output)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Decision analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
