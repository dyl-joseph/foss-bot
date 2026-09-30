#!/usr/bin/env python3
"""Install foss-bot into $HOME. Safe to rerun. Pass --dry-run to only print."""
import filecmp
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent
HOME = pathlib.Path(os.environ.get("FOSS_BOT_HOME") or pathlib.Path.home())
AGENTS = HOME / ".agents"
CLAUDE = HOME / ".claude"
CODEX = HOME / ".codex"
ENGINE = REPO / "engine"
DRY = "--dry-run" in sys.argv
BEGIN, END = "# >>> foss-bot >>>", "# <<< foss-bot <<<"
PSTACK_SKILLS = [
    "poteto-mode", "how", "why", "swarm", "arena", "architect", "interrogate", "reflect", "no-comments",
    "setup-pstack", "automate-me", "recall", "teach", "figure-it-out", "create-verification-skill",
    "maintain-verification-skill", "show-me-your-work", "blast-radius", "refactor",
]
POINTER = ("> **Harness.** This skill uses Cursor's vocabulary (`Task`, `subagent_type`, `model`, `readonly`, "
           "`run_in_background`, `environment: \"cloud\"`, `AskQuestion`, `.mdc` rules). In Claude Code or Codex, "
           "translate each one with `~/.agents/skills/poteto-mode/references/harness.md` before you act.")
BOT_UI_POINTER = ("> **Grok Bot hosts only.** `update_state`, `SendToUser`, routines, and the webhook URL exist only "
                  "inside Grok Bot. In Claude Code or Codex, say this skill does not apply and stop.")
LUNA_ROLES = {
    "qa": "Chief-of-staff QA bot: reproduces reports and verifies changes with proof.",
    "gardener": "Chief-of-staff gardener bot: lint rules, cleanup, verification-skill upkeep.",
    "scribe": "Chief-of-staff scribe bot: docs, PR descriptions, summaries.",
}


def say(msg):
    print(("[dry-run] " if DRY else "") + msg)


def write(path, text):
    say(f"write {path}")
    if DRY:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def link(src, dst):
    if dst.is_symlink() and dst.resolve() == src.resolve():
        return
    if dst.exists() or dst.is_symlink():
        same = dst.is_file() and src.is_file() and filecmp.cmp(src, dst, shallow=False)
        backup = HOME / ".foss-bot-backup" / dst.relative_to(HOME)
        say(f"{'replace' if same else 'back up'} {dst}" + ("" if same else f" -> {backup}"))
        if not DRY:
            if same:
                dst.unlink()
            else:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(dst, backup)
    say(f"link {dst} -> {src}")
    if not DRY:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.symlink_to(src)


def run(cmd, check=False):
    say("run " + " ".join(map(str, cmd)))
    if not DRY:
        subprocess.run(list(map(str, cmd)), check=check)


def have(tool):
    return shutil.which(tool) is not None


def install_engine():
    if not (ENGINE / "scripts/install-skills.sh").exists():
        run(["git", "-C", REPO, "submodule", "update", "--init"], check=True)
    run(["bash", ENGINE / "scripts/install-skills.sh", HOME])
    agentbox = ENGINE / "examples/linux/agentbox/agentbox"
    if not (HOME / ".local/bin/agentbox").exists():
        link(agentbox, HOME / ".local/bin/agentbox")


def install_skills():
    skill = REPO / "skills/chief-of-staff"
    link(skill, AGENTS / "skills/chief-of-staff")
    link(skill, CLAUDE / "skills/chief-of-staff")
    for bot in (skill / "references/bots").glob("*.md"):
        target = AGENTS / "bots" / bot.name
        if not target.exists():
            write(target, bot.read_text())
    link(REPO / "pstack/pstack-models.mdc", AGENTS / "rules/pstack-models.mdc")


def patch_pstack():
    root = AGENTS / "skills"
    if not (root / "poteto-mode").is_dir():
        say("pstack not found in ~/.agents/skills; install it, then rerun to add the harness map")
        return
    link(REPO / "pstack/harness.md", root / "poteto-mode/references/harness.md")
    if (root / "no-comments").is_dir():
        link(REPO / "pstack/comment-sicko.md", root / "no-comments/references/comment-sicko.md")
    for name in PSTACK_SKILLS:
        add_pointer(root / name / "SKILL.md", POINTER)
    add_pointer(root / "make-bot-ui/SKILL.md", BOT_UI_POINTER)
    for skill in root.iterdir():
        if skill.is_dir() and not (CLAUDE / "skills" / skill.name).exists():
            link(skill, CLAUDE / "skills" / skill.name)


def add_pointer(path, pointer):
    if not path.exists():
        return
    text = path.read_text()
    if "references/harness.md" in text or "Grok Bot hosts only" in text:
        return
    lines = text.split("\n")
    h1 = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if h1 is None:
        return
    lines[h1 + 1:h1 + 1] = ["", pointer]
    write(path, "\n".join(lines))


def install_claude():
    for hook in (REPO / "claude/hooks").glob("*.py"):
        link(hook, CLAUDE / "hooks" / hook.name)
    path = CLAUDE / "settings.json"
    settings = json.loads(path.read_text()) if path.exists() else {}
    settings.setdefault("extraKnownMarketplaces", {})["openai-codex"] = {
        "source": {"source": "github", "repo": "openai/codex-plugin-cc"}}
    settings.setdefault("enabledPlugins", {})["codex@openai-codex"] = True
    settings["forceLoginMethod"] = "claudeai"
    hooks = settings.setdefault("hooks", {})
    add_hook(hooks, "PreToolUse", "python3 ~/.claude/hooks/codex-only-subagents.py", "Agent|Task")
    add_hook(hooks, "SessionStart", "python3 ~/.claude/hooks/patch-codex-companion.py")
    write(path, json.dumps(settings, indent=2) + "\n")
    if have("claude") and not list((CLAUDE / "plugins").glob("*/openai-codex")):
        run(["claude", "plugin", "marketplace", "add", "openai/codex-plugin-cc"])
        run(["claude", "plugin", "install", "codex@openai-codex"])
    run(["python3", CLAUDE / "hooks/patch-codex-companion.py"])
    if have("claude") and have("cua-driver"):
        listed = subprocess.run(["claude", "mcp", "get", "cua-driver"], capture_output=True).returncode == 0
        if not listed:
            run(["claude", "mcp", "add", "-s", "user", "cua-driver", "--", shutil.which("cua-driver"), "mcp"])


def add_hook(hooks, event, command, matcher=None):
    groups = hooks.setdefault(event, [])
    if any(h.get("command") == command for g in groups for h in g.get("hooks", [])):
        return
    group = {"hooks": [{"type": "command", "command": command}]}
    if matcher:
        group = {"matcher": matcher, **group}
    groups.append(group)


def install_codex():
    for role in (REPO / "codex/agent-roles").glob("*.toml"):
        link(role, CODEX / "agent-roles" / role.name)
    rules = (REPO / "codex/rules/agentbox.rules").read_text().replace("{HOME}", str(HOME))
    write(CODEX / "rules/agentbox.rules", rules)
    path = CODEX / "config.toml"
    text = path.read_text() if path.exists() else ""
    if "forced_login_method" not in text:
        text = 'forced_login_method = "chatgpt"\n' + text
    block = [BEGIN]
    for name, desc in LUNA_ROLES.items():
        if f"[agents.{name}]" not in text:
            block += [f"[agents.{name}]", f'description = "{desc}"',
                      f'config_file = "{CODEX / "agent-roles" / (name + ".toml")}"', ""]
    cua = shutil.which("cua-driver")
    if cua and "[mcp_servers.cua-driver]" not in text:
        block += ["[mcp_servers.cua-driver]", f'command = "{cua}"', 'args = ["mcp"]', ""]
    if len(block) > 1 and BEGIN not in text:
        text = text.rstrip("\n") + "\n\n" + "\n".join(block + [END]) + "\n"
    write(path, text)


def install_agents_md():
    path = AGENTS / "AGENTS.md"
    text = path.read_text() if path.exists() else "# AGENTS.md\n"
    if "## foss-bot: team" not in text and "## pstack across harnesses" not in text:
        snippet = (REPO / "agents/AGENTS.foss-bot.md").read_text()
        write(path, text.rstrip("\n") + "\n\n<!-- foss-bot -->\n" + snippet + "<!-- /foss-bot -->\n")
    for target in (CLAUDE / "CLAUDE.md", CODEX / "AGENTS.md"):
        if not target.exists():
            link(path, target)


def check_auth():
    leaked = [k for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") if os.environ.get(k)]
    if leaked:
        say(f"warning: {', '.join(leaked)} is set; foss-bot expects subscription logins only. Unset it.")


def main():
    for tool in ("claude", "codex", "git"):
        if not have(tool):
            say(f"warning: {tool} not on PATH; its steps may be skipped")
    install_engine()
    install_skills()
    patch_pstack()
    install_claude()
    install_codex()
    install_agents_md()
    check_auth()
    say("done. Log in with `claude` (claude.ai) and `codex login` (ChatGPT).")


if __name__ == "__main__":
    main()
