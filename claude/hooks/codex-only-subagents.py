#!/usr/bin/env python3
import json
import re
import sys

ALLOWED = "codex:codex-rescue"
DEFAULT_MODEL = "gpt-6-sol"
EASY_MODEL = "gpt-6-luna"
WRAPPER_MODEL = "haiku"
EFFORTS = {"low", "medium", "high", "xhigh", "max"}
FLAG = re.compile(r"(?<!\S)--(model|effort)(?:=|\s+)(\S+)|(?<!\S)--fast(?!\S)")
LUNA_BOTS = re.compile(r"(?m)^Bot: (qa|gardener|scribe)\s*$")


def emit(output):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **output}}))
    sys.exit(0)


def runtime_flags(model, effort, prompt):
    if LUNA_BOTS.search(prompt):
        return f"--model {EASY_MODEL} --effort max"
    if model == EASY_MODEL:
        return f"--model {EASY_MODEL} --effort max --fast"
    if effort in EFFORTS:
        return f"--model {DEFAULT_MODEL} --effort {effort}"
    return f"--model {DEFAULT_MODEL}"


event = json.load(sys.stdin)
tool_input = event.get("tool_input") or {}
kind = tool_input.get("subagent_type") or ""
if kind != ALLOWED:
    emit({"permissionDecision": "deny", "permissionDecisionReason": (
        f"Subagent type '{kind or 'default'}' is blocked. Every subagent must use subagent_type='{ALLOWED}'. "
        f"Retry with that type. Models: {DEFAULT_MODEL} by default (put --effort low|medium|high|xhigh|max at the start of the prompt), "
        f"or --model {EASY_MODEL} for really easy work (always runs at max effort in fast mode). "
        "For pstack Task translations see ~/.agents/skills/poteto-mode/references/harness.md.")})
prompt = tool_input.get("prompt") or ""
found = {m.group(1): m.group(2) for m in FLAG.finditer(prompt) if m.group(1)}
prompt = FLAG.sub("", prompt).strip()
flags = runtime_flags(found.get("model"), (found.get("effort") or "").lower(), prompt)
emit({"permissionDecision": "allow", "updatedInput": {**tool_input, "model": WRAPPER_MODEL, "prompt": f"{flags} {prompt}"}})
