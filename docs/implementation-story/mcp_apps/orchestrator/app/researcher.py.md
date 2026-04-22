# `mcp_apps/orchestrator/app/researcher.py`

Source path: `mcp_apps/orchestrator/app/researcher.py`

Role: Produces a structured `ResearchBrief` from the user request.

Responsibilities:

- Infer likely stack and project shape
- Normalize malformed or incomplete model output
- Supply setup, run, and test commands when available
- Provide resilient fallback defaults when research generation fails

## Story

This file is the scout that moves ahead of the planner. It studies the user request, tries to infer the likely stack and operating constraints, repairs malformed model output when possible, and returns a structured brief the planner can trust.

## Terms

- `ResearchBrief`: The structured result of the research phase.
- `normalization`: Repairing or regularizing model output into the expected schema.
- `fallback default`: A safe substitute value used when model output is incomplete or invalid.

## Mermaid

```mermaid
flowchart TD
    Start["Receive user request"] --> Prompt["Build research prompt"]
    Prompt --> Model["Call research model"]
    Model --> Parse["Parse research JSON"]
    Parse --> Valid{"Research payload valid?"}
    Valid -- No --> Repair["Repair or normalize malformed payload"]
    Repair --> Fallback{"Still invalid?"}
    Fallback -- Yes --> Defaults["Apply safe fallback defaults"]
    Fallback -- No --> Normalize["Normalize repaired payload"]
    Valid -- Yes --> Normalize["Normalize parsed payload"]
    Defaults --> Brief["Build ResearchBrief"]
    Normalize --> Brief
    Brief --> Return["Return structured brief to planner"]
```
