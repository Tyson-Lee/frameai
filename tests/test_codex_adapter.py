from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from frameai.providers import ClaudeAdapter, CodexAdapter, get_provider


class CodexAdapterContractTests(unittest.TestCase):
    def test_availability_checks_codex_on_path(self):
        with patch("shutil.which", return_value="/bin/codex") as which:
            self.assertTrue(CodexAdapter().is_available())
        which.assert_called_once_with("codex")

    def test_run_preserves_prompt_boundary_cwd_and_exit_code(self):
        completed = subprocess.CompletedProcess(["codex"], 17)
        with patch("subprocess.run", return_value=completed) as run:
            result = CodexAdapter().run("prompt; $(not shell)", cwd=Path("/repo"))

        self.assertEqual(result.returncode, 17)
        run.assert_called_once_with(
            [
                "codex",
                "exec",
                "--ephemeral",
                "--dangerously-bypass-approvals-and-sandbox",
                "--cd",
                "/repo",
                "prompt; $(not shell)",
            ],
            cwd=Path("/repo"),
        )

    def test_run_preserves_archive_streams_and_environment(self):
        env = {"FRAMEAI_RUN_MODE": "cli"}
        completed = subprocess.CompletedProcess(["codex"], 0)
        with patch("subprocess.run", return_value=completed) as run:
            CodexAdapter().run(
                "run prompt",
                cwd=Path("/repo"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
            )

        run.assert_called_once_with(
            [
                "codex",
                "exec",
                "--ephemeral",
                "--dangerously-bypass-approvals-and-sandbox",
                "--cd",
                "/repo",
                "run prompt",
            ],
            cwd=Path("/repo"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )

    def test_codex_always_uses_no_sandbox_flag(self):
        completed = subprocess.CompletedProcess(["codex"], 0)
        with patch("subprocess.run", return_value=completed) as run:
            CodexAdapter().run("prompt", cwd=Path("/repo"))

        argv = run.call_args.args[0]
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", argv)
        self.assertNotIn("--sandbox", argv)
        self.assertEqual(argv[-3:], ["--cd", "/repo", "prompt"])

    def test_timeout_failure_is_not_retried_or_rewritten(self):
        failure = subprocess.TimeoutExpired(["codex", "exec"], 30)
        with patch("subprocess.run", side_effect=failure) as run:
            with self.assertRaises(subprocess.TimeoutExpired) as raised:
                CodexAdapter().run("prompt", cwd=Path("/repo"), timeout=30)
        self.assertIs(raised.exception, failure)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

    def test_subprocess_failures_are_not_retried_or_rewritten(self):
        failure = OSError("exec failed")
        with patch("subprocess.run", side_effect=failure) as run:
            with self.assertRaisesRegex(OSError, "exec failed"):
                CodexAdapter().run("prompt", cwd=Path("/repo"))
        self.assertEqual(run.call_count, 1)

    def test_relative_cwd_is_resolved_as_the_codex_workspace(self):
        completed = subprocess.CompletedProcess(["codex"], 0)
        with patch("subprocess.run", return_value=completed) as run:
            CodexAdapter().run("prompt", cwd=Path("relative-workspace"))

        workspace = Path("relative-workspace").resolve()
        self.assertEqual(run.call_args.args[0][-3:-1], ["--cd", str(workspace)])
        self.assertEqual(run.call_args.kwargs["cwd"], workspace)


class ProviderRegistryTests(unittest.TestCase):
    def test_default_adapters_are_explicit(self):
        self.assertIsInstance(get_provider("claude"), ClaudeAdapter)
        self.assertIsInstance(get_provider("codex"), CodexAdapter)

    def test_unknown_provider_fails_without_fallback(self):
        with self.assertRaisesRegex(ValueError, "unsupported provider 'other'"):
            get_provider("other")


class ProviderSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import runpy

        cls.frame = runpy.run_path(str(Path(__file__).parents[1] / "frame"))

    def test_claude_remains_default(self):
        parser = self.frame["build_parser"]()
        args = parser.parse_args(["add", "probe", "--dry-run"])
        with patch.dict("os.environ", {}, clear=True):
            adapter = self.frame["selected_provider"](args)
        self.assertIsInstance(adapter, ClaudeAdapter)

    def test_explicit_cli_provider_overrides_environment(self):
        parser = self.frame["build_parser"]()
        args = parser.parse_args(["add", "probe", "--provider", "codex"])
        with patch.dict("os.environ", {"FRAMEAI_PROVIDER": "claude"}, clear=True):
            adapter = self.frame["selected_provider"](args)
        self.assertIsInstance(adapter, CodexAdapter)


    def test_codex_selection_warns_that_sandbox_is_disabled(self):
        parser = self.frame["build_parser"]()
        args = parser.parse_args(["add", "probe", "--provider", "codex"])
        with patch.dict("os.environ", {}, clear=True), patch("sys.stderr") as stderr:
            adapter = self.frame["selected_provider"](args)
        self.assertIsInstance(adapter, CodexAdapter)
        output = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("sandbox are disabled", output)

    def test_removed_codex_bypass_option_is_rejected(self):
        parser = self.frame["build_parser"]()
        with self.assertRaises(SystemExit):
            parser.parse_args(["add", "probe", "--codex-bypass-sandbox"])


if __name__ == "__main__":
    unittest.main()
