---
description: Scaffold one RedAgent specialist agent following project conventions
---

Create a new agent in backend/agents/ following the EXACT conventions of the
existing agents and the architecture in CLAUDE.md sections 6 and 8.

Requirements:
- One job, one system prompt, one file
- Input/output strictly via contracts in backend/core/contracts.py
- Gemini 2.5 only
- Include a unit test that mocks the input contract and checks the output shape

Before writing: state which agent, its single job, and its input/output
contracts. Then build until the unit test passes.

Agent to scaffold: $ARGUMENTS
