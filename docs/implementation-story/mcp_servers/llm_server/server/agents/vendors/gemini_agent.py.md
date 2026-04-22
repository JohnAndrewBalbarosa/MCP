# `mcp_servers/llm_server/server/agents/vendors/gemini_agent.py`

Source path: `mcp_servers/llm_server/server/agents/vendors/gemini_agent.py`

Role: Gemini-specific generation adapter.

Responsibilities:

- Translate typed runtime settings into `google-genai` calls
- Return normalized plain-text outputs to the server layer

## Story

This file is a provider-specific adapter. It takes the generic runtime chosen by the system and turns it into a concrete SDK or API call for one vendor, then normalizes the returned text back into the common flow.

## Terms

- `vendor adapter`: A provider-specific implementation that calls one model backend.
- `SDK call`: The concrete library or API request used to obtain model output.
- `normalized text`: A provider response reduced to the common text form used elsewhere.

## Mermaid

```mermaid
flowchart TD
    Start["Entry point selects Gemini provider"] --> Config["Build Gemini generation config from runtime"]
    Config --> Call["Call google-genai SDK"]
    Call --> Normalize["Normalize returned text"]
    Normalize --> Return["Return Gemini response"]
```
