## foss-bot: team and harnesses
- This file loads in both Claude Code (`~/.claude/CLAUDE.md`) and Codex (`~/.codex/AGENTS.md`). Skills live once in `~/.agents/skills` and both harnesses read them.
- pstack skills were written for Cursor and Grok Bot. Before acting on a `Task` call, model slug, `readonly`, `environment: "cloud"`, `AskQuestion`, `/loop`, routine, Bugbot, or Origin step, translate it with `~/.agents/skills/poteto-mode/references/harness.md`.
- Per-role models: `~/.agents/rules/pstack-models.mdc`. Read it when a skill says to. Neither harness auto-loads `.mdc` rules.
- Multi-agent team (Grok Bot style): `/chief-of-staff` (`$chief-of-staff` in Codex). Bot personas live in `~/.agents/bots/`; each workspace's board is `~/.agents/cos/<slug>/board.md`.
- Cross-model seats: in Claude Code, `gpt-*` seats are Codex subagents and `claude-*` seats are the main thread. In Codex, `gpt-*` seats are `spawn_agent` and `claude-*` seats run through `claude -p --model claude-opus-5-5`.

## foss-bot: isolated computer use
- Use Agentbox for work that needs its own Linux desktop or browser. Read `~/.agents/skills/agentbox/SKILL.md` for setup, browser seeding, and MCP configuration.
- Give each concurrently active worker a unique Agentbox VM ID. Drive its desktop with `agentbox cua <id> <tool> '<json>'` or `agentbox mcp <id>`, and its terminal with `agentbox exec <id> -- <command>`. Keep a worker's GUI and terminal work on the same ID.
- Clone workers from the stopped `main` login seed. Host shell and filesystem tools stay outside the VM, so do not describe them as sandboxed.

## foss-bot: Claude Code only
- Every subagent is `codex:codex-rescue` (plugin `codex@openai-codex`). The hook `~/.claude/hooks/codex-only-subagents.py` blocks any other subagent type, pins the Codex model, and runs the forwarding wrapper on Haiku.
- Default model is `gpt-6-sol`. Choose its effort per task by starting the prompt with `--effort low|medium|high|xhigh|max`.
- For really easy work (renames, one-line edits, lookups), start the prompt with `--model gpt-6-luna`. The hook runs it at max effort in fast mode.
- The chief-of-staff bots QA, gardener, and scribe always run on `gpt-6-luna` at max effort without fast mode. The hook enforces this from the `Bot:` line in their persona. In Codex, spawn them with `agent_type` `qa`, `gardener`, or `scribe`.
- Codex and Claude run on subscription logins only (ChatGPT for Codex, claude.ai for Claude Code). Never use or set an API key.
- Code-writing subagents that run in parallel use `isolation: "worktree"` on the `Agent` call. Cap them at 4 at once.
