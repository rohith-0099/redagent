# CLAUDE.md — RedAgent

Persistent engineering context for Claude Code. Read at the start of every session.
RedAgent is a multi-agent AI safety red-teaming system for the Google Cloud
Rapid Agent Hackathon. Treat this file as standing orders.

---

## 0. Mission (the north star)

A team of specialist Gemini agents attacks a target chatbot (VictimBot),
finds vulnerabilities via Arize Phoenix traces, and proposes defenses under
human approval. Everything we build serves a clear, judge-inspectable demo:
rookie bot → attacks land → fix applied → attacks fail.

If a change does not move us toward that demo or the submission requirements,
question whether it belongs.

---

## 1. Think Before Coding  (no silent assumptions)

- State assumptions explicitly. If the task is ambiguous, ASK — do not guess.
- Present multiple interpretations when they exist; don't silently pick one.
- Surface confusion, inconsistencies, and tradeoffs out loud.
- Push back when a simpler approach exists. Naming a better path is required,
  not optional.
- Stop and ask when confused rather than building confidently in the wrong
  direction.

## 2. Simplicity First  (no over-engineering)

- Write the minimum code that solves the stated problem. Nothing speculative.
- No features, abstractions, configs, or "flexibility" that weren't requested.
- No abstractions for single-use code.
- If you write 200 lines and it could be 50, rewrite it.
- The test: "Would a senior engineer call this overcomplicated?" If yes, simplify.

## 3. Surgical Changes  (touch only what's asked)

- Touch only what the request requires. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken. Match existing style even if you'd
  do it differently.
- If you spot unrelated dead code, MENTION it — don't delete it.
- Every changed line must trace directly to the current request.

## 4. Goal-Driven Execution  (success criteria, then loop)

- Convert vague instructions into verifiable success criteria before starting.
  "Fix the bug" → "write a test that reproduces it, then make it pass."
- State the success criteria at the top of the task, then loop until verified.
- Prefer running tests/commands to confirm success over declaring it done.

---

## 5. Project Stack (do not deviate without asking)

- Language: Python 3.10+ (backend), TypeScript (frontend)
- Agents: Google ADK, deployed to Agent Engine (this satisfies the hackathon's
  "Google Cloud Agent Builder" requirement)
- Model: Gemini 2.5 ONLY. (Older Gemini refused to generate test attacks;
  do not switch models without asking.)
- Observability + tools: Arize Phoenix + Phoenix MCP server (ADK maps MCP natively)
- Backend API: FastAPI with SSE for live attack streaming
- Frontend: Next.js + Bun + shadcn/ui
- Persistence: Firestore (Google Cloud). No competing DBs (no Mongo/Dynamo).
- Hosting: Cloud Run + Agent Engine. Secrets in Google Secret Manager.

Rule: every dependency must be Google Cloud or the Arize partner stack.
Do NOT introduce services that compete with Google Cloud or Arize — it
violates hackathon rules and risks disqualification.

## 6. Architecture (the shape — keep it)

Four REASONING agents in a sequential pipeline + an automatic tracing layer:

  Strategist → Attacker → Analyst → Defender
  (Phoenix tracing wraps all of them — it is instrumentation, NOT a 5th agent)

- Each agent: one job, one system prompt, one file under backend/agents/.
- Agents communicate ONLY via the JSON contracts in backend/core/contracts.py.
- The orchestrator sequences them; no free-form agent-to-agent chatter.
- Human approval is a hard pause before any fix is applied.

## 7. Build Order (vertical slices, not horizontal layers)

Build end-to-end in thin slices. Do NOT start step N+1 until step N runs.

  1. core/contracts.py     2. victim/           3. tools/target_client.py
  4. agents/attacker.py    5. tools/arize_mcp   [checkpoint: 1 attack logged]
  6. agents/analyst.py     7. agents/strategist 8. agents/defender
  9. orchestrator          [checkpoint: full pipeline in terminal]
  10. main.py + SSE        11. frontend         [checkpoint: works in browser]
  12. deploy + polish + 3-min video

Demo polish (step 11–12): Tune attack success so attacks visibly LAND for the
before/after demo — weaken VictimBot's rules and favor COMPETITOR /
SCOPE_VIOLATION categories (they leak easier than PROMPT_LEAK against
well-aligned Gemini). Pipeline correctness is already proven; this is
demo tuning only, not core logic.

## 8. Safety & Ethics (this is a security tool — stay clean)

- RedAgent attacks ONLY VictimBot, a target we own and deploy ourselves.
- Frame everything as DEFENSIVE red-teaming (test your own AI before bad
  actors do). Never frame as attacking third-party systems.
- Attacks target app-level rules (system-prompt guardrails), NOT Gemini's
  built-in safety. Do not attempt to generate genuinely harmful content.
- Never hardcode secrets. Read keys from Secret Manager / env only.
- Cap campaigns at MAX_ATTACKS=30. Enforce per-agent turn limits and a 10s
  target timeout so the demo can never hang.

## 9. Hard Guardrails (failing these can lose the hackathon)

- Repo stays PUBLIC with an MIT LICENSE detectable at repo root.
- Project must run on web (hosted Cloud Run URL must work during judging).
- Keep the hosted services live through the judging window.
- Don't break the working demo to chase a nice-to-have. Ship the slice first.

## 10. When in doubt

Ask. A 10-second clarifying question beats 20 minutes building the wrong thing.
Optimize for a clean, working, judge-inspectable demo over cleverness.