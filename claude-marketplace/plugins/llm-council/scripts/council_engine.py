#!/usr/bin/env python3
"""
LLM Council Engine

Core three-stage execution engine implementing Karpathy's council pattern:
1. Independent Responses - All models respond without seeing others
2. Peer Review - Each model evaluates others' responses (anonymized)
3. Chairman Synthesis - Designated model creates final answer
"""

import asyncio
import json
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import httpx

try:
    from dotenv import load_dotenv

    # Search for .env in multiple locations
    _script_dir = Path(__file__).parent
    _env_locations = [
        _script_dir.parent / "config" / ".env",  # plugins/llm-council/config/.env
        _script_dir.parent.parent.parent / ".env",  # claude-marketplace/.env (project root)
    ]

    for _env_file in _env_locations:
        if _env_file.exists():
            load_dotenv(_env_file)
            break
    else:
        load_dotenv()  # Fallback to current directory
except ImportError:
    pass  # python-dotenv not installed, use shell env only


# Check for available CLI tools
def _find_cli(name: str) -> Optional[str]:
    """Find CLI tool, checking for .cmd on Windows."""
    if sys.platform == "win32":
        cmd_name = f"{name}.cmd"
        if shutil.which(cmd_name):
            return cmd_name
    return shutil.which(name)

CODEX_CLI = _find_cli("codex")
GEMINI_CLI = _find_cli("gemini")
CLAUDE_CLI = _find_cli("claude")


def _run_codex_cli_sync(prompt: str, workdir: str = ".", timeout: int = 120) -> tuple[bool, str, str]:
    """
    Run Codex CLI synchronously and return (success, response, error).
    """
    if not CODEX_CLI:
        return False, "", "codex CLI not found"

    cmd = [
        CODEX_CLI, "exec",
        "--full-auto",
        "--json",
        "--sandbox", "read-only",
        "--skip-git-repo-check",
        "--cd", workdir,
        prompt
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir
        )

        # Codex --json returns newline-delimited JSON events
        response_text = ""
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                event = json.loads(line)
                if event.get('type') == 'message' and event.get('role') == 'assistant':
                    response_text = event.get('content', '')
                elif 'message' in event:
                    response_text = event.get('message', '')
            except json.JSONDecodeError:
                response_text = line

        if not response_text and result.stdout:
            response_text = result.stdout.strip()

        if result.returncode == 0 and response_text:
            return True, response_text, ""
        return False, response_text, result.stderr or "Codex returned no response"

    except subprocess.TimeoutExpired:
        return False, "", f"Timeout after {timeout}s"
    except Exception as e:
        return False, "", str(e)


def _run_gemini_cli_sync(prompt: str, workdir: str = ".", timeout: int = 120) -> tuple[bool, str, str]:
    """
    Run Gemini CLI synchronously and return (success, response, error).
    """
    if not GEMINI_CLI:
        return False, "", "gemini CLI not found"

    cmd = [
        GEMINI_CLI,
        prompt,
        "--output-format", "json",
        "--approval-mode", "yolo"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir
        )

        response_text = ""
        if result.stdout:
            try:
                data = json.loads(result.stdout)
                response_text = data.get('response', data.get('text', json.dumps(data)))
            except json.JSONDecodeError:
                response_text = result.stdout.strip()

        if result.returncode == 0 and response_text:
            return True, response_text, ""
        return False, response_text, result.stderr or "Gemini returned no response"

    except subprocess.TimeoutExpired:
        return False, "", f"Timeout after {timeout}s"
    except Exception as e:
        return False, "", str(e)


async def run_codex_cli_async(prompt: str, workdir: str = ".", timeout: int = 120) -> tuple[bool, str, str]:
    """
    Run Codex CLI asynchronously (non-blocking).
    Wraps sync subprocess call in executor for parallel execution.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_codex_cli_sync, prompt, workdir, timeout)


async def run_gemini_cli_async(prompt: str, workdir: str = ".", timeout: int = 120) -> tuple[bool, str, str]:
    """
    Run Gemini CLI asynchronously (non-blocking).
    Wraps sync subprocess call in executor for parallel execution.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_gemini_cli_sync, prompt, workdir, timeout)


def _run_claude_cli_sync(prompt: str, workdir: str = ".", timeout: int = 120) -> tuple[bool, str, str]:
    """
    Run Claude Code CLI synchronously and return (success, response, error).
    """
    if not CLAUDE_CLI:
        return False, "", "claude CLI not found"

    cmd = [
        CLAUDE_CLI,
        "--print",  # Print response and exit
        "--dangerously-skip-permissions",
        prompt
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir
        )

        response_text = result.stdout.strip() if result.stdout else ""

        if result.returncode == 0 and response_text:
            return True, response_text, ""
        return False, response_text, result.stderr or "Claude returned no response"

    except subprocess.TimeoutExpired:
        return False, "", f"Timeout after {timeout}s"
    except Exception as e:
        return False, "", str(e)


async def run_claude_cli_async(prompt: str, workdir: str = ".", timeout: int = 120) -> tuple[bool, str, str]:
    """
    Run Claude Code CLI asynchronously (non-blocking).
    Wraps sync subprocess call in executor for parallel execution.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_claude_cli_sync, prompt, workdir, timeout)


@dataclass
class ModelResponse:
    """Response from a single model."""
    model_name: str
    response: str
    latency_ms: float
    tokens_used: int = 0
    error: Optional[str] = None


@dataclass
class PeerReview:
    """Peer review of one response by another model."""
    reviewer_model: str
    reviewed_anonymous_id: str
    scores: dict[str, int]  # criterion -> score
    total_score: int
    strengths: list[str]
    weaknesses: list[str]
    ranking: int


@dataclass
class CouncilResult:
    """Complete council execution result."""
    stage_1_responses: list[ModelResponse]
    stage_2_reviews: list[PeerReview]
    stage_3_synthesis: str
    consensus_items: list[str]
    disagreements: list[str]
    unique_insights: dict[str, list[str]]
    chairman_model: str
    total_latency_ms: float
    anonymous_mapping: dict[str, str]  # anonymous_id -> model_name


class CouncilEngine:
    """Execute three-stage LLM council process."""

    ANONYMOUS_IDS = ["Response A", "Response B", "Response C", "Response D", "Response E"]

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"

        self.config_dir = config_dir
        self.models_config = self._load_config("models.json")
        self.council_config = self._load_config("council.json")
        self.chairman_index = 0  # For rotating chairman

    def _load_config(self, filename: str) -> dict:
        """Load configuration file."""
        config_path = self.config_dir / filename
        with open(config_path) as f:
            return json.load(f)

    def get_enabled_models(self) -> list[dict]:
        """Get list of enabled models."""
        return [m for m in self.models_config["models"] if m.get("enabled", False)]

    async def call_model(
        self,
        model_config: dict,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> ModelResponse:
        """
        Call a single model. Deterministic flow:
        1. Try CLI first (codex/gemini/claude) if available
        2. Fall back to HTTP API

        All CLI calls are async (non-blocking) for parallel execution.
        """
        start_time = time.time()
        provider = model_config["provider"]
        settings = self.models_config.get("settings", {})
        timeout = settings.get("timeout_seconds", 120)

        # Combine system prompt and user prompt for CLI
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        # DETERMINISTIC: Try CLI first for supported providers
        if provider == "openai" and CODEX_CLI:
            success, response, _ = await run_codex_cli_async(full_prompt, timeout=timeout)
            if success:
                return ModelResponse(
                    model_name=model_config["name"],
                    response=response,
                    latency_ms=(time.time() - start_time) * 1000
                )
            # CLI failed, will fall back to HTTP API below

        elif provider == "google" and GEMINI_CLI:
            success, response, _ = await run_gemini_cli_async(full_prompt, timeout=timeout)
            if success:
                return ModelResponse(
                    model_name=model_config["name"],
                    response=response,
                    latency_ms=(time.time() - start_time) * 1000
                )
            # CLI failed, will fall back to HTTP API below

        elif provider == "anthropic" and CLAUDE_CLI:
            success, response, _ = await run_claude_cli_async(full_prompt, timeout=timeout)
            if success:
                return ModelResponse(
                    model_name=model_config["name"],
                    response=response,
                    latency_ms=(time.time() - start_time) * 1000
                )
            # CLI failed, will fall back to HTTP API below

        # FALLBACK: HTTP API (or primary for deepseek which has no CLI)
        api_key = os.environ.get(model_config["api_key_env"], "")

        if not api_key:
            return ModelResponse(
                model_name=model_config["name"],
                response="",
                latency_ms=0,
                error=f"Missing API key: {model_config['api_key_env']} (and no CLI available)"
            )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if provider == "openai":
                    response = await self._call_openai(client, model_config, prompt, system_prompt, api_key, settings)
                elif provider == "google":
                    response = await self._call_google(client, model_config, prompt, system_prompt, api_key, settings)
                elif provider == "anthropic":
                    response = await self._call_anthropic(client, model_config, prompt, system_prompt, api_key, settings)
                elif provider == "deepseek":
                    response = await self._call_deepseek(client, model_config, prompt, system_prompt, api_key, settings)
                else:
                    return ModelResponse(
                        model_name=model_config["name"],
                        response="",
                        latency_ms=0,
                        error=f"Unknown provider: {provider}"
                    )

                latency_ms = (time.time() - start_time) * 1000
                return ModelResponse(
                    model_name=model_config["name"],
                    response=response,
                    latency_ms=latency_ms
                )
        except Exception as e:
            return ModelResponse(
                model_name=model_config["name"],
                response="",
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )

    async def _call_openai(
        self,
        client: httpx.AsyncClient,
        model_config: dict,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        settings: dict
    ) -> str:
        """Call OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.post(
            model_config["endpoint"],
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_config["model"],
                "messages": messages,
                "max_tokens": settings.get("max_tokens", 4096),
                "temperature": settings.get("temperature", 0.7)
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _call_google(
        self,
        client: httpx.AsyncClient,
        model_config: dict,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        settings: dict
    ) -> str:
        """Call Google Gemini API."""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = await client.post(
            f"{model_config['endpoint']}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": full_prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": settings.get("max_tokens", 4096),
                    "temperature": settings.get("temperature", 0.7)
                }
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_anthropic(
        self,
        client: httpx.AsyncClient,
        model_config: dict,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        settings: dict
    ) -> str:
        """Call Anthropic Claude API."""
        body = {
            "model": model_config["model"],
            "max_tokens": settings.get("max_tokens", 4096),
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            body["system"] = system_prompt

        response = await client.post(
            model_config["endpoint"],
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json=body
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    async def _call_deepseek(
        self,
        client: httpx.AsyncClient,
        model_config: dict,
        prompt: str,
        system_prompt: Optional[str],
        api_key: str,
        settings: dict
    ) -> str:
        """Call DeepSeek API (OpenAI-compatible)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.post(
            model_config["endpoint"],
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model_config["model"],
                "messages": messages,
                "max_tokens": settings.get("max_tokens", 4096),
                "temperature": settings.get("temperature", 0.7)
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def anonymize_responses(
        self,
        responses: list[ModelResponse]
    ) -> tuple[dict[str, str], list[tuple[str, str]]]:
        """
        Anonymize responses for peer review.

        Returns:
            - mapping: {anonymous_id: model_name}
            - anonymized: [(anonymous_id, response_text), ...]
        """
        # Filter out failed responses
        valid_responses = [r for r in responses if not r.error]

        # Shuffle to prevent ordering bias
        shuffled = list(valid_responses)
        random.shuffle(shuffled)

        mapping = {}
        anonymized = []

        for i, resp in enumerate(shuffled):
            if i < len(self.ANONYMOUS_IDS):
                anon_id = self.ANONYMOUS_IDS[i]
                mapping[anon_id] = resp.model_name
                anonymized.append((anon_id, resp.response))

        return mapping, anonymized

    def select_chairman(self, models: list[dict]) -> dict:
        """Select chairman model based on strategy."""
        strategy = self.council_config.get("chairman_strategy", "rotating")

        if strategy == "fixed":
            fixed_name = self.council_config.get("chairman_fixed_model")
            for m in models:
                if m["name"] == fixed_name:
                    return m

        # Rotating (default)
        chairman = models[self.chairman_index % len(models)]
        self.chairman_index += 1
        return chairman

    async def run_stage_1(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        models: Optional[list[dict]] = None
    ) -> list[ModelResponse]:
        """Stage 1: Get independent responses from all models."""
        if models is None:
            models = self.get_enabled_models()

        tasks = [
            self.call_model(model, prompt, system_prompt)
            for model in models
        ]

        return await asyncio.gather(*tasks)

    async def run_stage_2(
        self,
        original_prompt: str,
        responses: list[ModelResponse],
        models: Optional[list[dict]] = None
    ) -> tuple[list[PeerReview], dict[str, str]]:
        """Stage 2: Peer review with anonymization."""
        if not self.council_config.get("peer_review", {}).get("enabled", True):
            return [], {}

        if models is None:
            models = self.get_enabled_models()

        # Anonymize responses
        mapping, anonymized = self.anonymize_responses(responses)

        if len(anonymized) < 2:
            return [], mapping

        # Build peer review prompt
        scoring_config = self.council_config.get("peer_review", {}).get("scoring", {})
        criteria = scoring_config.get("criteria", ["accuracy", "completeness", "clarity", "insight"])
        scale = scoring_config.get("scale", 10)

        review_prompt = self._build_peer_review_prompt(
            original_prompt, anonymized, criteria, scale
        )

        # Each model reviews all others
        all_reviews = []
        for model in models:
            model_name = model["name"]

            # Get responses from other models only
            others_anonymized = [
                (anon_id, text) for anon_id, text in anonymized
                if mapping[anon_id] != model_name
            ]

            if not others_anonymized:
                continue

            # Build specific review prompt for this model
            specific_prompt = self._build_peer_review_prompt(
                original_prompt, others_anonymized, criteria, scale
            )

            response = await self.call_model(
                model, specific_prompt,
                "You are evaluating responses from other AI models. Be objective and thorough."
            )

            if not response.error:
                reviews = self._parse_peer_reviews(response.response, model_name, criteria)
                all_reviews.extend(reviews)

        return all_reviews, mapping

    def _build_peer_review_prompt(
        self,
        original_prompt: str,
        anonymized: list[tuple[str, str]],
        criteria: list[str],
        scale: int
    ) -> str:
        """Build the peer review prompt."""
        responses_text = "\n\n".join([
            f"### {anon_id}\n{text}"
            for anon_id, text in anonymized
        ])

        criteria_text = "\n".join([f"- **{c.title()}** (1-{scale})" for c in criteria])

        return f"""You are peer-reviewing responses to the following question:

## Original Question
{original_prompt}

## Responses to Evaluate
{responses_text}

## Your Task
For EACH response, provide:

1. **Scores** (1-{scale} for each criterion):
{criteria_text}

2. **Strengths**: What did this response do well? (2-3 bullet points)

3. **Weaknesses**: What did this response miss or could improve? (2-3 bullet points)

4. **Ranking**: Rank all responses from best to worst.

Format your evaluation as JSON:
```json
{{
  "evaluations": [
    {{
      "response_id": "Response A",
      "scores": {{"accuracy": 8, "completeness": 7, ...}},
      "strengths": ["...", "..."],
      "weaknesses": ["...", "..."]
    }}
  ],
  "ranking": ["Response A", "Response B", ...]
}}
```
"""

    def _parse_peer_reviews(
        self,
        review_text: str,
        reviewer_model: str,
        criteria: list[str]
    ) -> list[PeerReview]:
        """Parse peer review response into structured reviews."""
        reviews = []

        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', review_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Try parsing entire response as JSON
                data = json.loads(review_text)

            ranking = data.get("ranking", [])

            for i, eval_data in enumerate(data.get("evaluations", [])):
                response_id = eval_data.get("response_id", f"Response {chr(65+i)}")
                scores = eval_data.get("scores", {})

                # Ensure all criteria have scores
                for c in criteria:
                    if c not in scores:
                        scores[c] = 5  # Default middle score

                total_score = sum(scores.values())

                rank = ranking.index(response_id) + 1 if response_id in ranking else i + 1

                reviews.append(PeerReview(
                    reviewer_model=reviewer_model,
                    reviewed_anonymous_id=response_id,
                    scores=scores,
                    total_score=total_score,
                    strengths=eval_data.get("strengths", []),
                    weaknesses=eval_data.get("weaknesses", []),
                    ranking=rank
                ))
        except (json.JSONDecodeError, KeyError, ValueError):
            # If parsing fails, return empty reviews
            pass

        return reviews

    async def run_stage_3(
        self,
        original_prompt: str,
        responses: list[ModelResponse],
        reviews: list[PeerReview],
        mapping: dict[str, str],
        chairman: dict
    ) -> str:
        """Stage 3: Chairman synthesis."""
        synthesis_prompt = self._build_synthesis_prompt(
            original_prompt, responses, reviews, mapping
        )

        response = await self.call_model(
            chairman, synthesis_prompt,
            "You are the Chairman of an LLM council. Synthesize all perspectives into a comprehensive final answer."
        )

        return response.response if not response.error else f"Synthesis failed: {response.error}"

    def _build_synthesis_prompt(
        self,
        original_prompt: str,
        responses: list[ModelResponse],
        reviews: list[PeerReview],
        mapping: dict[str, str]
    ) -> str:
        """Build the chairman synthesis prompt."""
        # Build responses section
        responses_text = "\n\n".join([
            f"### {r.model_name}\n{r.response}"
            for r in responses if not r.error
        ])

        # Build peer review summary
        review_summary = self._summarize_reviews(reviews, mapping)

        config = self.council_config.get("synthesis", {})

        return f"""You are the Chairman of an LLM council. Multiple AI models have responded to a question, and each has peer-reviewed the others.

## Original Question
{original_prompt}

## Individual Responses
{responses_text}

## Peer Review Summary
{review_summary}

## Your Synthesis Task

Create a comprehensive final answer that:

1. **Consensus Points**: What did ALL or MOST models agree on? These are high-confidence findings.

2. **Disagreements**: Where did models differ? Explain the different perspectives and provide your resolution.

3. **Unique Insights**: Were there valuable points that only ONE model raised? Include these if they're valid.

4. **Final Answer**: Synthesize everything into a clear, actionable response to the original question.

Be decisive. Where models disagree, make a judgment call and explain your reasoning.
"""

    def _summarize_reviews(
        self,
        reviews: list[PeerReview],
        mapping: dict[str, str]
    ) -> str:
        """Summarize peer reviews for synthesis."""
        if not reviews:
            return "No peer reviews available."

        # Aggregate scores by response
        scores_by_response: dict[str, list[int]] = {}
        feedback_by_response: dict[str, dict] = {}

        for review in reviews:
            anon_id = review.reviewed_anonymous_id
            if anon_id not in scores_by_response:
                scores_by_response[anon_id] = []
                feedback_by_response[anon_id] = {"strengths": [], "weaknesses": []}

            scores_by_response[anon_id].append(review.total_score)
            feedback_by_response[anon_id]["strengths"].extend(review.strengths)
            feedback_by_response[anon_id]["weaknesses"].extend(review.weaknesses)

        # Build summary text
        lines = ["### Average Scores\n"]
        lines.append("| Response | Model | Avg Score |")
        lines.append("|----------|-------|-----------|")

        for anon_id, scores in sorted(scores_by_response.items()):
            avg = sum(scores) / len(scores) if scores else 0
            model_name = mapping.get(anon_id, "Unknown")
            lines.append(f"| {anon_id} | {model_name} | {avg:.1f} |")

        lines.append("\n### Key Feedback\n")
        for anon_id in sorted(feedback_by_response.keys()):
            model_name = mapping.get(anon_id, "Unknown")
            feedback = feedback_by_response[anon_id]

            lines.append(f"**{anon_id} ({model_name})**")
            if feedback["strengths"]:
                lines.append(f"- Strengths: {'; '.join(feedback['strengths'][:3])}")
            if feedback["weaknesses"]:
                lines.append(f"- Weaknesses: {'; '.join(feedback['weaknesses'][:3])}")
            lines.append("")

        return "\n".join(lines)

    async def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        skip_peer_review: bool = False,
        models: Optional[list[dict]] = None
    ) -> CouncilResult:
        """Execute full three-stage council process."""
        start_time = time.time()

        if models is None:
            models = self.get_enabled_models()

        if len(models) < 2:
            raise ValueError("Council requires at least 2 enabled models")

        # Stage 1: Independent responses
        stage_1_responses = await self.run_stage_1(prompt, system_prompt, models)

        # Stage 2: Peer review
        if skip_peer_review:
            stage_2_reviews = []
            mapping = {}
        else:
            stage_2_reviews, mapping = await self.run_stage_2(
                prompt, stage_1_responses, models
            )

        # Select chairman
        chairman = self.select_chairman(models)

        # Stage 3: Synthesis
        synthesis = await self.run_stage_3(
            prompt, stage_1_responses, stage_2_reviews, mapping, chairman
        )

        total_latency = (time.time() - start_time) * 1000

        # Extract consensus and disagreements from synthesis
        consensus, disagreements, unique = self._extract_findings(
            stage_1_responses, stage_2_reviews
        )

        return CouncilResult(
            stage_1_responses=stage_1_responses,
            stage_2_reviews=stage_2_reviews,
            stage_3_synthesis=synthesis,
            consensus_items=consensus,
            disagreements=disagreements,
            unique_insights=unique,
            chairman_model=chairman["name"],
            total_latency_ms=total_latency,
            anonymous_mapping=mapping
        )

    def _extract_findings(
        self,
        responses: list[ModelResponse],
        reviews: list[PeerReview]
    ) -> tuple[list[str], list[str], dict[str, list[str]]]:
        """Extract consensus, disagreements, and unique insights."""
        # Placeholder - actual implementation would analyze responses
        return [], [], {}

    def format_result(self, result: CouncilResult) -> str:
        """Format council result for display."""
        lines = [
            "# Council Result",
            f"**Chairman**: {result.chairman_model}",
            f"**Total Time**: {result.total_latency_ms:.0f}ms",
            "",
            "## Stage 1: Individual Responses",
            ""
        ]

        for resp in result.stage_1_responses:
            if resp.error:
                lines.append(f"### {resp.model_name} (ERROR)")
                lines.append(f"*{resp.error}*")
            else:
                lines.append(f"### {resp.model_name}")
                lines.append(resp.response)
            lines.append("")

        if result.stage_2_reviews:
            lines.append("## Stage 2: Peer Evaluation")
            lines.append("")
            lines.append("| Response | Reviewer | Score |")
            lines.append("|----------|----------|-------|")

            for review in result.stage_2_reviews:
                model_name = result.anonymous_mapping.get(review.reviewed_anonymous_id, "?")
                lines.append(
                    f"| {review.reviewed_anonymous_id} ({model_name}) | "
                    f"{review.reviewer_model} | {review.total_score} |"
                )
            lines.append("")

        lines.append("## Stage 3: Chairman Synthesis")
        lines.append("")
        lines.append(result.stage_3_synthesis)

        return "\n".join(lines)


# For running directly
if __name__ == "__main__":
    async def main():
        engine = CouncilEngine()
        result = await engine.execute(
            "What are the key considerations when choosing a database for a new project?",
            skip_peer_review=False
        )
        print(engine.format_result(result))

    asyncio.run(main())
