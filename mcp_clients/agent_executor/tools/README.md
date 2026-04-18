# Agent Executor Tools

Deterministic helper modules used by ephemeral executor agents.

## Modules
- flow_parser.py: parses DAG interdependencies, branch width, and merge points
  to guide executor lifecycle and parallel flow handling.
- response_parser.py: Parses generated code output, strips fences, and produces
  compact function summaries so downstream agents can use abstractions instead
  of re-reading full files.

## Purpose
- Separate parsing/tooling concerns from worker agent execution logic.
- Keep prompts and summaries consistent across all executor nodes.
