---
name: excalidraw
description: |
  Create hand-drawn style diagrams as Excalidraw JSON files. Use when the user asks for
  architecture diagrams, flowcharts, sequence diagrams, or any visual documentation
  that benefits from a sketch/whiteboard aesthetic.
user-invocable: true
argument-hint: "[description of diagram]"
---

# Excalidraw Diagram Generator

Create `.excalidraw` JSON files that can be opened in [Excalidraw](https://excalidraw.com/) or rendered via the excalidraw-render MCP server.

## Output Format

Write valid Excalidraw JSON to a `.excalidraw` file. The format is:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "claude",
  "elements": [...],
  "appState": {
    "viewBackgroundColor": "#ffffff"
  }
}
```

## Element Types

### Rectangle
```json
{
  "type": "rectangle",
  "id": "unique-id",
  "x": 100, "y": 100,
  "width": 200, "height": 80,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#a5d8ff",
  "fillStyle": "hachure",
  "strokeWidth": 2,
  "roundness": { "type": 3 },
  "boundElements": [{ "type": "text", "id": "text-id" }]
}
```

### Text
```json
{
  "type": "text",
  "id": "text-id",
  "x": 150, "y": 130,
  "text": "Service",
  "fontSize": 20,
  "fontFamily": 1,
  "textAlign": "center",
  "containerId": "rect-id"
}
```

### Arrow
```json
{
  "type": "arrow",
  "id": "arrow-id",
  "x": 300, "y": 140,
  "width": 100, "height": 0,
  "points": [[0, 0], [100, 0]],
  "startBinding": { "elementId": "source-id", "focus": 0, "gap": 1 },
  "endBinding": { "elementId": "target-id", "focus": 0, "gap": 1 },
  "strokeColor": "#1e1e1e",
  "strokeWidth": 2
}
```

### Ellipse
```json
{
  "type": "ellipse",
  "id": "ellipse-id",
  "x": 100, "y": 100,
  "width": 150, "height": 150
}
```

## Guidelines

- Use unique IDs for all elements (short descriptive strings like `"api-box"`, `"db-arrow"`)
- Bind text to containers via `containerId` and `boundElements`
- Connect arrows with `startBinding` and `endBinding`
- Use `hachure` fill for the hand-drawn look
- Color palette: `#a5d8ff` (blue), `#b2f2bb` (green), `#ffd8a8` (orange), `#ffc9c9` (red), `#d0bfff` (purple)
- Space elements with 50-100px gaps
- Keep text concise — labels, not paragraphs
- Save as `docs/diagrams/<name>.excalidraw` or alongside relevant code

## Rendering

If the excalidraw-render MCP server is configured, diagrams can be rendered to PNG:

```
mcp:excalidraw render docs/diagrams/architecture.excalidraw
```

Otherwise, open the `.excalidraw` file at https://excalidraw.com/ or in VS Code with the Excalidraw extension.
