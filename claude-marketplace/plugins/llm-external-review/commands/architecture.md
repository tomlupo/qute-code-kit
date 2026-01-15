# /llm-external-review:architecture

> **This command invokes EXTERNAL AI (Gemini) for architecture review. Claude must NOT do this review itself.**

Review overall architecture and design decisions using Gemini's 1M token context.

## Usage

```
/llm-external-review:architecture [<directory>] [--scope <scope>]
```

## Arguments

- `<directory>` - (Optional) Directory to analyze (default: current project)
- `--scope` - (Optional) Focus: full, api, data, ml, frontend

## Behavior

1. **Analyze project structure**
   - Scan directory tree
   - Identify key components
   - Map dependencies

2. **Identify patterns**
   - Design patterns in use
   - Architectural style (monolith, microservices, etc.)
   - Layer separation

3. **Review against best practices**
   - SOLID principles
   - DRY/KISS
   - Separation of concerns

4. **Generate architecture review**:
   ```
   🏗️ Architecture Review
   ━━━━━━━━━━━━━━━━━━━━━

   ## Project Structure
   ```
   src/
   ├── api/          # REST API layer
   ├── core/         # Business logic
   ├── data/         # Data access
   ├── ml/           # ML models
   └── utils/        # Shared utilities
   ```

   ## Patterns Identified
   - ✅ Repository pattern (data layer)
   - ✅ Service layer (core)
   - ⚠️ Some controllers have business logic

   ## Strengths
   - Clear separation of API and core
   - Good use of dependency injection
   - Consistent naming conventions

   ## Concerns

   ### 🔴 Critical
   - Circular dependency: core → ml → core

   ### 🟡 Improvements
   - api/handler.py: 500+ lines, consider splitting
   - No clear error handling strategy

   ## Recommendations
   1. Extract shared ML utils to break cycle
   2. Split large handlers into sub-modules
   3. Implement centralized error handling

   ## Dependency Graph
   ```
   api → core → data
           ↓
          ml ← (circular!)
   ```
   ```

## Example

```
/llm-external-review:architecture --scope ml

# Output:
🏗️ ML Architecture Review
━━━━━━━━━━━━━━━━━━━━━━━━

## ML Components
- models/: 5 model definitions
- training/: Training pipelines
- inference/: Prediction services
- evaluation/: Metrics & validation

## Patterns
- ✅ Model registry pattern
- ✅ Feature store abstraction
- ⚠️ Training scripts not using config

## Concerns
- No model versioning strategy
- Inference coupled to training code

## Recommendations
1. Add MLflow for experiment tracking
2. Separate inference into standalone service
3. Implement feature validation
```
