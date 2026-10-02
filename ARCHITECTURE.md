# Architecture — Jemi Agent

## Overview

Jemi is a single-process CLI application that wraps the Claude API in an agentic loop. The user types a message; the agent sends it to Claude with a set of tool schemas; Claude either responds directly or requests a tool call; the agent executes the tool and feeds the result back; this repeats until Claude produces a final answer.

## Request Flow

    User input
        |
        v
    chat() --> Anthropic API (Claude)
                   |
            stop_reason?
            /                  end_turn         tool_use
          |                |
    Print response     run_tool()
    to terminal            |
                   read_file / list_directory / search_web
                           |
                   Append result to conversation
                           |
                   Loop back to API

## Key Design Decisions

**Why a single agentic loop instead of a ReAct chain?**
The Anthropic tool-use API handles the reasoning loop natively via stop_reason: tool_use. Claude decides when to call tools and when it has enough information to answer — fewer moving parts, less to debug.

**Why DuckDuckGo over a paid search API?**
No key required, no rate limits for reasonable usage. Swapping to Serper or Brave Search later is a one-function change in search_tool.py.

**Why Rich for the UI?**
Panels, spinners, and markdown rendering in ~10 lines, works on every terminal without configuration.

**Why config.py instead of environment variables?**
For a personal CLI tool, a gitignored config.py is simpler. Production deployments would use env vars — easy swap.

## File Responsibilities

| File | Responsibility |
|------|---------------|
| agent.py | Agentic loop, UI rendering, CLI entry point |
| config.py | API key, model name, constants (gitignored) |
| tools/file_tool.py | read_file, list_directory |
| tools/search_tool.py | search_web via DuckDuckGo |

## Adding a New Tool

1. Write the function in tools/your_tool.py with a docstring and type hints
2. Add its JSON schema to TOOL_SCHEMAS in agent.py
3. Add it to TOOL_FUNCTIONS map in agent.py

Claude will automatically decide when to use it.

## Planned Extensions

- Ollama backend for offline use
- Flask + React web UI with streaming responses
- MCP integration for plug-in tool ecosystem
