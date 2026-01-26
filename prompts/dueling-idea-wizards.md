# The Dueling Idea Wizards

**Source:** @doodlestein (Jeffrey Emanuel) - "My Favorite Prompts" series (January 16, 2026)

**Purpose:** Requires 2 agents (e.g., CC Opus 4.5 and Codex GPT-5.2 with high reasoning). Involves generating ideas, evaluating them, and having the agents critique each other.

## Setup

First, have both agents review the project's code or plan documents:

```
First read ALL of the AGENTS .md file and README .md file super carefully and understand ALL of both! Then use your code investigation agent mode to fully understand the code and technical architecture and purpose of the project.
```

Then give each agent the original Idea Wizard Prompt:

```
Come up with your very best ideas for improving this project to make it more robust, reliable, performant, intuitive, user-friendly, ergonomic, useful, compelling, etc. while still being obviously accretive and pragmatic. Come up with 30 ideas and then really think through each idea carefully, how it would work, how users are likely to perceive it, how we would implement it, etc; then winnow that list down to your VERY best 5 ideas. Explain each of the 5 ideas in order from best to worst and give your full, detailed rationale and justification for how and why it would make the project obviously better and why you're confident of that assessment. Use ultrathink.
```

## Cross-Evaluation Prompt

After they respond, tell each agent:

```
I asked another model the same thing and it came up with this list:

<paste the output from the other model here>

Now, I want you to very carefully consider and evaluate each of them and then give me your candid evaluation and score them from 0 (worst) to 1000 (best) as an overall score that reflects how good and smart the idea is, how useful in practical, real-life scenarios it would be for humans and ai coding agents like yourself, how practical it would be to implement it all correctly, whether the utility/advantages of the new feature/idea would easily justify the increased complexity and tech debt, etc. Use ultrathink
```

## Final Counter-Evaluation

Then, show each model how the other model rated their ideas:

```
I asked the other model the exact same thing, to score YOUR ideas using the same grading methodology; here is what it came up with:

<paste the output from the other model here>
```
