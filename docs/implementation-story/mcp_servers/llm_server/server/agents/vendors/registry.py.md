# `mcp_servers/llm_server/server/agents/vendors/registry.py`

Source path: `mcp_servers/llm_server/server/agents/vendors/registry.py`

Role: Provider registry and capability lookup.

Responsibilities:

- Map provider ids to concrete generator functions
- Report whether a provider supports batch generation
- Centralize provider dispatch metadata

## Story

This file is a provider-specific adapter. It takes the generic runtime chosen by the system and turns it into a concrete SDK or API call for one vendor, then normalizes the returned text back into the common flow.

## Terms

- `vendor adapter`: A provider-specific implementation that calls one model backend.
- `SDK call`: The concrete library or API request used to obtain model output.
- `normalized text`: A provider response reduced to the common text form used elsewhere.

## Mermaid

```mermaid
flowchart TD
    Start["Provider id is requested"] --> Match["Match provider id in registry"]
    Match --> ReturnGen["Return single generator"]
    Match --> ReturnBatch["Return batch generator if available"]
```
