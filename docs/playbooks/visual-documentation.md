# Visual Documentation

> Turn complex terminal output into styled, shareable HTML pages.

## Components

| Component | Source | Purpose |
|-----------|--------|---------|
| visual-explainer | `claude-plugins-official` plugin | Convert terminal output to styled HTML |
| gist-report | `gist-report` skill | Share reports via GitHub gist |
| image-generator | `image-generator` skill | Generate diagrams and visuals |
| architecture-diagram | `architecture-diagram` skill | Dark-themed HTML+SVG system architecture diagrams |
| playground | `claude-plugins-official` plugin | Build interactive explorers |

## When to Use

- Explaining architecture to stakeholders who don't read terminal output
- Sharing code review summaries with the team
- Creating visual documentation from CLI output
- Making test results, dependency trees, or schemas presentable

## Approaches

### A. Auto-visualization with visual-explainer

The plugin auto-activates for complex tables (4+ rows or 3+ columns). For explicit use:

```
/visual-explainer
```

It routes content to the right format:
| Content type | Visualization |
|-------------|---------------|
| Flowcharts, architecture | Mermaid diagrams |
| Layouts, component hierarchies | CSS Grid |
| Data, comparisons | HTML tables with sorting |
| Metrics, trends | Chart.js dashboards |

Output: self-contained HTML in `~/.agent/diagrams/` → opens in browser.

**Creative uses:**
```
Show me the dependency graph of src/ as a visual diagram
```
```
Create a visual diff summary of the last 5 commits
```
```
Visualize our database schema with relationships
```

### B. Custom visual reports with playground

For interactive exploration rather than static visualization:

```
Create a playground that shows our API endpoint structure
with expandable sections, search, and response examples
```

Playground creates self-contained HTML tools with:
- Interactive controls (sliders, dropdowns, search)
- Real-time filtering and sorting
- Dark/light theme support
- No dependencies — single file, works offline

**Creative uses:**
```
Build a playground that visualizes our test coverage
by module with pass/fail status and trend charts
```
```
Create an interactive explorer for our config options
showing defaults, types, and descriptions
```

### C. Generated diagrams with image-generator

For visuals that need to look polished:

```
Generate a clean architecture diagram showing our data flow:
Ingestion → Processing → Storage → API → Dashboard
Use --style technical-diagram, dark background
```

### D. System diagrams with architecture-diagram

Model-invocable skill (Cocoon AI, MIT) that produces a single self-contained
`.html` file with inline SVG, semantic color-coding (cyan frontends, emerald
backends, violet databases, amber cloud, rose security, orange message buses),
JetBrains Mono typography, and a dark `#020617` theme. Copies a starter template
from `assets/template.html` and customizes viewBox, components, arrows, legend,
and summary cards.

Trigger phrases that route here: *"architecture diagram"*, *"infrastructure
diagram"*, *"cloud architecture"*, *"network topology"*, *"security diagram"*.

**Example usages:**

```
Use the architecture-diagram skill to diagram a React + FastAPI + Postgres app
behind CloudFront, with Auth0 OAuth for login and S3 for asset storage.
Save as docs/architecture/web-app.html.
```

```
Create an AWS serverless architecture diagram: API Gateway → Lambda (Python) →
DynamoDB, with SQS for async jobs, EventBridge for cron, and Cognito for auth.
Show the us-west-2 region boundary and a security group around the API layer.
```

```
Diagram our microservices topology: 4 Go services behind an NGINX ingress on
Kubernetes, Kafka event bus between order-service and inventory-service,
Postgres per service, Redis cache, Prometheus + Grafana for observability.
```

```
Read src/ and infer the component graph, then render it with the
architecture-diagram skill — one box per top-level package, arrows for imports,
a violet box for the shared datastore, and a summary card listing entry points.
```

Compared with `image-generator` (rasterized PNGs) and `visual-explainer`
(Mermaid / Chart.js), `architecture-diagram` is the right pick when you want
editable SVG in a single HTML file that renders identically on any machine —
good for README embeds, PR artifacts, or stakeholder handoffs.

### E. Share via gist

Any of the above can be shared:

```
/gist-report
```

Creates a shareable GitHub gist URL. Works for HTML reports, Markdown summaries, or any structured output.

## Example Combinations

### Architecture review for stakeholders
```
1. Analyze the codebase structure
2. /visual-explainer → Mermaid architecture diagram
3. /gist-report → shareable URL
4. Send to team Slack
```

### Polished architecture HTML for a design review
```
1. Describe components + flows (or let Claude infer from the repo)
2. architecture-diagram skill → docs/architecture/<project>.html
3. Open locally to verify spacing / legend placement
4. /gist-report → paste URL into the review doc
```

### Test failure dashboard
```
1. Run tests, capture results
2. Create a playground with pass/fail breakdown, failure details, trend
3. /gist-report → link in PR comment
```

### Database migration plan
```
1. Show current vs proposed schema
2. /visual-explainer → side-by-side schema visualization
3. Generate image of migration flow → image-generator --style technical-diagram
4. Combine in gist-report
```

## Tips

- visual-explainer works best with structured data — feed it clean output, not raw logs
- Playground is better for interactive exploration; visual-explainer for static reports
- For recurring reports, save the playground HTML and regenerate data only
- Combine with `/handoff` to note which visualizations need updating
- Reach for `architecture-diagram` over Mermaid when you need precise layout
  control, named security groups / region boundaries, or a branded dark theme
  you can commit into the repo
