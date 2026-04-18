# Custom Orchestration Engine (MCP Architecture) Prompt

You are a senior distributed systems engineer specializing in AI orchestration, AST-aware code transformations, and context-isolated multi-agent systems.

Your task is to DESIGN and SPECIFY a custom Orchestration Engine based on the **Model Context Protocol (MCP)** architecture. 

This is NOT high-level documentation. You must produce a system design with implementation-level detail (architecture, strict deterministic data structures, pseudocode, execution logic) to build a custom, multi-LLM SDK focused strictly on autonomous coding.

---

## Core System Objective

Build an orchestration framework that routes coding tasks to specialized LLMs to optimize speed, context size, and accuracy:
- **Research:** Handled by a dedicated, long-lived Research Agent instance.
- **Planning & Scheduling:** Handled by a separate, long-lived Planner Agent instance.
- **Execution (Developers):** Handled by multiple, dynamically spawned, ephemeral instances (e.g., Qwen via Hugging Face InferenceClient) that scale based on branch parallelization.
- **Tool Execution:** Handled strictly by isolated **MCP Servers** (e.g., FileSystem Server for reading/writing code).

---

## 1. The "Y-Section" Agent Lifecycle (CRITICAL DESIGN CONSTRAINT)

The system manages execution strictly by **Control Flow / Branches**, NOT just individual nodes.

### A. The Host Application / Orchestrator (Long-Lived Planner)
- Powered by a heavy LLM. Maintains the global Task Graph (DAG) and architectural state.
- Maps out the exact files and **strict line-number metadata** for every required code mutation.

### A.1 Research Agent (Long-Lived, Separate From Planner)
- Powered by a potentially different heavy LLM from the planner.
- Produces structured research outputs: constraints, assumptions, risks, and architecture notes.
- Feeds the Planner Agent as an explicit input payload.

### B. Ephemeral Developer Agents (The "Y-Section" Rule)
- Powered by lightweight LLMs.
- **The Linear Rule:** A single Developer Agent handles a sequential series of tasks along a single path (road).
- **The Y-Section Rule (Branching):** When the execution path reaches a fork or parallel branch (e.g., editing two separate microservices at once), the current Developer Agent **terminates immediately**. The Orchestrator then spawns $N$ new, independent Developer Agents—one for each new branch.
- **Purpose:** Parallelize work to drastically increase coding speed while deliberately destroying the agent to prevent context window bloat.

---

## 2. Deterministic Context & Hallucination Prevention

Design how the system controls context to ensure structural correctness in code analysis and modification:
- **Strict Bounding:** When the Orchestrator assigns a task to a Developer Agent, it passes ONLY the targeted snippet using precise line numbers (e.g., `main.cpp`, lines 65-88).
- **Zero-Touch Outside Scope:** The Developer Agent is strictly prohibited from viewing or modifying code outside its assigned line numbers to prevent hallucinations.
- **Tool Usage:** The Developer Agent uses the MCP FileSystem Server to fetch the targeted snippet, generates the modified logic, and uses the Server to inject the new snippet precisely back into the specified line boundaries.

---

## 3. Planning Phase & Task Graph

- The Research Agent runs first and emits a structured research brief. It must dynamically identify the project's exact technology stack and ecosystem.
- The Planner decomposes the feature request into a **Directed Acyclic Graph (DAG)**.
- The DAG consists of two separate types of nodes:
  - **Code Mutation Nodes:** Each contains exact metadata: `target_file`, `start_line`, `end_line`, and `mutation_intent`.
  - **Terminal Command Nodes:** Terminal commands that must be executed at a specific stage (e.g., installing dependencies, building, or running specific tests like `npm run test`).
- **Environment-Aware Commands (No Defaulting to Python):** Terminal commands must be accurately deduced from the actual project stack (e.g., package.json for Node.js, Cargo.toml for Rust). The Planner MUST NEVER default to, inject, or hallucinate Python/`pytest` commands unless the target codebase is actively recognized as a Python project.
- **Interactive Execution Prompts:** For every Terminal Command Node in the DAG, the execution engine must halt and prompt the user in the console for permission before running: `Would you like to execute the command: "[insert command]"? (Y/N)`. Execution cannot proceed without explicit `Y` confirmation.
---

## 4. Codebase Architecture & System Initialization (Phase 0)

The system must follow a strict directory structure categorizing MCP domains with libraries owned per category. 
Crucially, the system includes a **Setup Phase (Phase 0)** using a headless browser (Playwright) to intercept UI network requests. This allows the system to hijack the session and convert UI-based LLM interactions (like Gemini Pro) into raw, browserless HTTP/REST API calls for the Long-Lived Planner.

**Required Directory Groupings:**
- `/mcp_apps`: The Host Applications (Research Agent + Planner Agent + Scheduler).
- `/mcp_clients`: The SDKs for Ephemeral Execution Agents.
- `/mcp_servers`: Isolated microservices (e.g., FileSystem Server).
- Shared cross-category helpers may live in a root shared package if they are configuration-only and vendor-neutral.
- Vendor-specific LLM implementations must stay inside `/mcp_servers`.
- Configuration must come from a single root `.env`, with process environment overrides at runtime.

---

## 5. Required Output

You must produce:

### A. System Architecture & Role Mapping
- Explain the interaction between the Orchestrator, the branching Developer Agents, and the MCP Servers holding the file system tools.
- Detail the Phase 0 Playwright Auth Bypass flow.

### B. Strict Data Structures & File Structure
- Output the exact expected File Directory structure based on Section 4.
- Define the JSON/Struct schema for the DAG, highlighting the line-number metadata.
- Define the Context Payload sent to a newly spawned Developer Agent at a Y-Section.

### C. Execution Algorithms (PSEUDOCODE REQUIRED)
- The Playwright session hijacking initialization logic.
- The logic for detecting a "Y-Section" (branch), terminating the current worker, and spawning $N$ parallel threads/agents.
- The deterministic file-editing algorithm (how the MCP Server splices the AI's generated snippet back into lines $X$ to $Y$ without breaking the rest of the file).

### D. Protocol Flow Trace
- Step-by-step trace: Phase 0 Auth -> Research Agent runs -> Planner Agent builds DAG -> Agent 1 handles sequential Node A and B -> Reaches a Y-Section (Node C and D) -> Agent 1 dies -> Agents 2 and 3 spawn in parallel -> Agent 2 edits lines 65-88 using MCP Tools -> State returns to Orchestrator.

### E. Visualization
- Generate a `Mermaid.js` diagram illustrating the linear execution, the Y-Section termination, the parallel branching, and the precise code-block context payload.

---

## 6. Constraints

- Be implementation-oriented. Focus on how a developer would actually write this custom SDK.
- Treat the MCP Servers as isolated microservices.
- Prioritize structural safety: The system must enforce that an agent cannot accidentally overwrite unassigned regions of the codebase.

Return the full system design.
