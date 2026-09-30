# pstack harness map

pstack was written for Cursor and Grok Bot. On this machine it runs in Claude Code and Codex, directly or inside T3 Code. When a skill names a Cursor or Grok Bot primitive, do the matching action for your harness from this file. Do not skip a step because its primitive is missing here. Translate it instead.

You are in Claude Code when you have the `Agent` and `Skill` tools. You are in Codex when you have `spawn_agent` and skills are invoked as `$name`.

## Subagents (`Task` calls)

A pstack `Task` call has a `subagent_type`, a `model`, and flags. Translate all of them per call.

| pstack says | Claude Code | Codex |
| --- | --- | --- |
| Any `Task` call, any `subagent_type` (`generalPurpose`, `poteto-agent`, `Comment Sicko`, ...) | `Agent` with `subagent_type: "codex:codex-rescue"`. A hook blocks every other type and pins Codex `gpt-6.1-sol`. Pick effort with `--effort <level>` at the start of the prompt. For trivial work, start with `--model gpt-6-luna`, which runs at max effort in fast mode. A prompt containing `Bot: qa`, `Bot: gardener`, or `Bot: scribe` is forced to `gpt-6-luna` at max effort without fast mode. | `spawn_agent`, then `wait_agent` for the result. For the QA, gardener, and scribe bots, set `agent_type` to `qa`, `gardener`, or `scribe` (roles in `~/.codex/config.toml` pin `gpt-6-luna` at max effort). |
| `subagent_type: "poteto-agent"` | Start the prompt with `Use the poteto-mode skill.` | Start the prompt with `$poteto-mode`. |
| A `subagent_type` that names a persona with its own file (e.g. `Comment Sicko`) | Paste that persona file into the prompt, then the task. | Same. |
| `model` is a `gpt-*` slug | `codex:codex-rescue`. Leave the model to the hook. | `spawn_agent`. |
| `model` is a `claude-*` slug | You are that seat. Do the pass yourself in the main thread. Write your result before you read the other seats' output, so it stays independent. | Run Claude Code headless: `claude -p --model claude-opus-5-5 --effort high --permission-mode plan "<prompt>"`. Use `--permission-mode bypassPermissions` only when the seat must write files. |
| `model` is a `grok-*` slug, `auto`, or `inherit-parent` | Use the `gpt-*` row. | Use the `gpt-*` row. |
| `readonly: true` | Say `Read-only. Do not edit files.` in the prompt. The wrapper then drops `--write`. | Say it in the prompt. For a Claude seat, use `--permission-mode plan`. |
| `readonly: false` "for MCP access" | The Codex subagent has only Codex's MCP servers. Fetch MCP-only evidence (tickets, chat, traces) yourself and pass it in the prompt. | `spawn_agent` inherits your MCP servers. |
| `run_in_background: true` | Set `run_in_background: true` on the `Agent` call. Put `--background` in the prompt only for read-only work that is not in a worktree. | `spawn_agent` is already asynchronous. |
| `environment: "cloud"` / "spawn a cloud agent" | There is no cloud here. Use a local background subagent. A worker that writes code gets its own worktree: `isolation: "worktree"` on the `Agent` call and `--wait` in the prompt, so the worktree still has the changes when the wrapper returns. | The worker's first step is `git worktree add ../<repo>-wt/<task> -b <branch>`, and it edits only that directory. |
| "Spawn N in one message" | N `Agent` calls in one response. | N `spawn_agent` calls, then one `wait_agent` per agent. |

Run at most 4 code-writing workers at once. Each one holds a full checkout and its own dev server. Read-only fan-out has no cap beyond the skill's own.

A panel that lists three families (for example `claude, gpt, grok`) keeps its size. Fill the missing family with a second `gpt-*` seat, and give that seat a different angle in its prompt so it does not repeat the first seat.

Codex and Claude run on subscription logins (ChatGPT, claude.ai). Never set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for a seat.

## Model roles

Read `~/.agents/rules/pstack-models.mdc` when a skill tells you to. Cursor loads it automatically. Claude Code and Codex do not. Its `gpt-*` and `claude-*` values map through the table above.

## Skills and modes

| pstack says | Claude Code | Codex |
| --- | --- | --- |
| `/skill-name`, "the **x** skill" | `Skill` tool, or `/x` | `$x` |
| Leaf `SKILL.md` path | `~/.agents/skills/<name>/SKILL.md` | same |
| Cursor Custom Mode, `mode: true`, the pinned `reminder:` | Not supported. Re-apply `/poteto-mode` at the start of each new task in the thread. | Re-apply `$poteto-mode`. |
| `AskQuestion` | `AskUserQuestion` (T3 Code shows it as a picker). | `request_user_input` when it is available. Otherwise ask one numbered multiple-choice question and end the turn. |
| Cursor's built-in `create-skill` | The `prompt-writing` skill plus `skill-creator`. | Same. |

## Loops, routines, and background work

| pstack or Grok Bot says | Claude Code | Codex |
| --- | --- | --- |
| `/loop until X`, "run until done" | The `/loop` skill. It paces itself with `ScheduleWakeup`. | `/goal X`. Codex keeps working until the goal's predicate holds. |
| Grok Bot routine, Cursor Automation, "daily `/maintain-verification-skill`" | `/schedule` creates a cloud routine (the repo must be on GitHub). For a run on this machine, use a systemd user timer. See below. | systemd user timer running `codex exec`. |
| A long task to hand off and forget | `claude --bg -p "<prompt>"`, then `claude agents` or `claude logs <id>`. | `codex exec "<prompt>"` in a background shell, or `codex queue`. |
| Grok Bot's team of bots, a coordinator bot, "spawn a cloud agent" from a bot | The `chief-of-staff` skill: this chat coordinates a roster in `~/.agents/bots/` and tracks work on `~/.agents/cos/<slug>/board.md`. | Same skill. |
| Grok Bot `SendToUser`, `update_state`, webhook routines | Grok Bot only. The `make-bot-ui` skill does not apply here. | Same. |

Local routine. Replace `<name>`, `<repo>`, the schedule, and the prompt.

```ini
# ~/.config/systemd/user/<name>.service
[Service]
Type=oneshot
WorkingDirectory=<repo>
ExecStart=%h/.local/bin/claude -p --permission-mode bypassPermissions "/maintain-verification-skill"

# ~/.config/systemd/user/<name>.timer
[Timer]
OnCalendar=*-*-* 09:00
Persistent=true
[Install]
WantedBy=timers.target
```

Then run `systemctl --user daemon-reload && systemctl --user enable --now <name>.timer`. Creating a timer is a durable change. Confirm it with the user first.

## Review, CI, and shipping

| pstack says | Here |
| --- | --- |
| Bugbot, "the agentic security review" | Greptile. Comment `@greptileai` on the PR, as the global AGENTS.md says. Triage its comments with `references/bugbot-triage.md`. For a local pass, use `/code-review` (Claude Code) or `codex review` (Codex). |
| Origin | `gh`. Origin is not installed. |
| `cursor-team-kit` `deslop` | The local `deslop` skill. |
| `cursor-team-kit` `control-ui` | The project's own control skill from `/create-verification-skill`, when it has one. Otherwise, for a web page in T3 Code with Claude Code, use the `mcp__t3-code__preview_*` tools (open, snapshot, click, screenshot, recording). In Codex, use its browser tool. For a native app or browser chrome, use the `cua-driver` skill. |
| `cursor-team-kit` `control-cli` | Run the CLI directly. For a TUI, drive it in `tmux` and read the pane with `tmux capture-pane -p`. |
| Visual proof, "show me a video" | The `record` skill. |

## Transcripts (recall, reflect, session-pickup)

pstack's path `~/.agents/projects/<slug>/agent-transcripts/` is Cursor's. Use these instead. T3 Code threads write to the same files.

- Claude Code: `~/.claude/projects/<slug>/<session-id>.jsonl`. `<slug>` is the workspace path with every `/` replaced by `-`, keeping the leading one (`/home/you/proj` becomes `-home-you-proj`). A session's subagent transcripts sit in `<session-id>/subagents/`.
- Codex: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`. The first line is `session_meta`. Filter chats by its `payload.cwd`.

Search both stores. The user switches between harnesses on the same project.

## Scripts

`poteto-mode/scripts` (`orch`, `watch-pr`, `bootstrap.ts`) need `bun`. It is installed through mise.
