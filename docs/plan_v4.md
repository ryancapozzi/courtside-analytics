# Plan v4 (Locked)

## Constraints
- Game-level NBA analytics only
- Dataset-first approach (free source, easiest reliable option)
- Season coverage based on dataset availability
- Local Ollama for LLM tasks
- 30-question benchmark
- Visualization optional and de-prioritized

## Milestones
1. Source + schema lock
2. ETL with validation and repeatable loading
3. Intent + entity resolution layer
4. Template SQL engine (primary path)
5. LLM fallback SQL + safety guardrails
6. Insight generation (highest priority)
7. CLI + 30-question evaluation
8. Optional visualization stretch

## Quality Bar
- Answers must be database-grounded
- SQL must be read-only and schema-valid
- Ambiguous requests must trigger clarifying prompts
- Responses should include metrics used and caveats when relevant
