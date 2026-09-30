#!/usr/bin/env python3
"""Teach the openai-codex plugin `--effort max` and `--fast` (priority service tier).

Idempotent. Runs on SessionStart so a plugin update gets re-patched.
Prints nothing unless a patch fails to apply.
"""
import pathlib
import sys

ROOT = pathlib.Path.home() / ".claude/plugins"
MARK = "/* pstack-patch: fast */"

COMPANION = [
    ('new Set(["none", "minimal", "low", "medium", "high", "xhigh"])',
     'new Set(["none", "minimal", "low", "medium", "high", "xhigh", "max"])'),
    ('[--effort <none|minimal|low|medium|high|xhigh>] [prompt]',
     '[--effort <none|minimal|low|medium|high|xhigh|max>] [--fast] [prompt]'),
    ('booleanOptions: ["json", "write", "resume-last", "resume", "fresh", "background"],',
     'booleanOptions: ["json", "write", "resume-last", "resume", "fresh", "background", "fast"],'),
    ("function buildTaskRequest({ cwd, model, effort, prompt, write, resumeLast, jobId }) {\n  return {\n    cwd,\n    model,\n    effort,",
     "function buildTaskRequest({ cwd, model, effort, fast, prompt, write, resumeLast, jobId }) {\n  return {\n    cwd,\n    model,\n    effort,\n    fast,"),
    ("      effort,\n      prompt,\n      write,\n      resumeLast,\n      jobId: job.id\n    });",
     "      effort,\n      fast: Boolean(options.fast),\n      prompt,\n      write,\n      resumeLast,\n      jobId: job.id\n    });"),
    ("        effort,\n        prompt,\n        write,\n        resumeLast,\n        jobId: job.id,\n        onProgress: progress",
     "        effort,\n        fast: Boolean(options.fast),\n        prompt,\n        write,\n        resumeLast,\n        jobId: job.id,\n        onProgress: progress"),
    ("    effort: request.effort,\n    sandbox: request.write",
     f"    effort: request.effort,\n    serviceTier: request.fast ? \"priority\" : null, {MARK}\n    sandbox: request.write"),
]

CODEX_LIB = [
    ("        model: options.model,\n        sandbox: options.sandbox,\n        ephemeral: false\n      });",
     "        model: options.model,\n        serviceTier: options.serviceTier,\n        sandbox: options.sandbox,\n        ephemeral: false\n      });"),
    ("        model: options.model,\n        sandbox: options.sandbox,\n        ephemeral: options.persistThread ? false : true,",
     "        model: options.model,\n        serviceTier: options.serviceTier,\n        sandbox: options.sandbox,\n        ephemeral: options.persistThread ? false : true,"),
    ("    serviceName: SERVICE_NAME,\n    ephemeral: options.ephemeral ?? true\n  };",
     f"    serviceName: SERVICE_NAME,\n    ephemeral: options.ephemeral ?? true,\n    ...(options.serviceTier ? {{ serviceTier: options.serviceTier }} : {{}}) {MARK}\n  }};"),
    ('    approvalPolicy: options.approvalPolicy ?? "never",\n    sandbox: options.sandbox ?? "read-only"\n  };',
     '    approvalPolicy: options.approvalPolicy ?? "never",\n    sandbox: options.sandbox ?? "read-only",\n    ...(options.serviceTier ? { serviceTier: options.serviceTier } : {})\n  };'),
]

RESCUE_AGENT = [
    ("- Treat `--effort <value>` and `--model <value>` as runtime controls and do not include them in the task text you pass through.",
     "- Treat `--effort <value>`, `--model <value>`, and `--fast` as runtime controls and do not include them in the task text you pass through. Pass `--fast` through to `task` unchanged. <!-- pstack-patch: fast -->"),
    ("- Leave `--effort` unset unless the user explicitly requests a specific reasoning effort.\n- Leave model unset by default. Only add `--model` when the user explicitly asks for a specific model.",
     "- Pass through any `--model`, `--effort`, and `--fast` flags at the start of the request exactly as given. Do not add or change them."),
]


def patch(path: pathlib.Path, edits):
    text = path.read_text()
    original = text
    for old, new in edits:
        if new in text:
            continue
        if old not in text:
            print(f"patch-codex-companion: {path}: anchor not found, plugin changed: {old[:60]!r}", file=sys.stderr)
            return
        text = text.replace(old, new, 1)
    if text != original:
        path.write_text(text)


for companion in ROOT.glob("*/openai-codex/**/scripts/codex-companion.mjs"):
    plugin = companion.parent.parent
    targets = [
        (plugin / "scripts/codex-companion.mjs", COMPANION),
        (plugin / "scripts/lib/codex.mjs", CODEX_LIB),
        (plugin / "agents/codex-rescue.md", RESCUE_AGENT),
    ]
    for path, edits in targets:
        if path.exists():
            patch(path, edits)
