# Visual Documentation

> Turn complex terminal output into styled, shareable HTML pages.

## Components

| Component | Source | Purpose |
|-----------|--------|---------|
| visual-explainer | `claude-plugins-official` plugin | Convert terminal output to styled HTML |
| gist-report | `gist-report` skill | Share reports via GitHub gist |
| image-generator | `image-generator` skill | Generate diagrams and visuals |
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

### D. Share via gist

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
