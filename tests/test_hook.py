import json
import pathlib
import subprocess
import unittest

HOOK = pathlib.Path(__file__).resolve().parent.parent / "claude/hooks/codex-only-subagents.py"


def run(tool_input):
    out = subprocess.run(["python3", str(HOOK)], input=json.dumps({"tool_input": tool_input}),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["hookSpecificOutput"]


def prompt_for(prompt):
    return run({"subagent_type": "codex:codex-rescue", "prompt": prompt})["updatedInput"]["prompt"]


class HookTest(unittest.TestCase):
    def test_blocks_other_subagent_types(self):
        self.assertEqual(run({"subagent_type": "general-purpose", "prompt": "x"})["permissionDecision"], "deny")

    def test_default_is_sol_and_keeps_effort(self):
        self.assertEqual(prompt_for("do it"), "--model gpt-6-sol do it")
        self.assertEqual(prompt_for("--effort high do it"), "--model gpt-6-sol --effort high do it")

    def test_other_models_are_pinned_to_sol(self):
        self.assertEqual(prompt_for("--model gpt-5.5 --fast do it"), "--model gpt-6-sol do it")

    def test_easy_model_runs_max_fast(self):
        self.assertEqual(prompt_for("--model gpt-6-luna rename x"), "--model gpt-6-luna --effort max --fast rename x")

    def test_luna_bots_run_max_without_fast(self):
        for bot in ("qa", "gardener", "scribe"):
            p = prompt_for(f"--model gpt-6-sol --fast --effort low\nBot: {bot}\ncheck it")
            self.assertTrue(p.startswith("--model gpt-6-luna --effort max "), p)
            self.assertNotIn("--fast", p)

    def test_other_bots_keep_sol(self):
        self.assertTrue(prompt_for("--effort high\nBot: engineer\nbuild").startswith("--model gpt-6-sol --effort high"))

    def test_wrapper_pinned_to_haiku(self):
        self.assertEqual(run({"subagent_type": "codex:codex-rescue", "prompt": "x"})["updatedInput"]["model"], "haiku")


if __name__ == "__main__":
    unittest.main()
