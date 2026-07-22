from __future__ import annotations

import contextlib
import io
import os
import runpy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


FRAME_PATH = Path(__file__).parents[1] / "frame"


class FakeAdapter:
    def __init__(self, name: str, returncode: int = 0, write_output: bool = False):
        self.name = name
        self.executable = name
        self.display_name = f"Fake {name}"
        self.invocation_label = f"fake {name} stdout"
        self.returncode = returncode
        self.write_output = write_output
        self.calls: list[tuple[str, dict[str, object]]] = []

    def is_available(self) -> bool:
        return True

    def run(self, prompt: str, **kwargs: object) -> subprocess.CompletedProcess:
        self.calls.append((prompt, kwargs))
        if self.write_output:
            env = kwargs["env"]
            assert isinstance(env, dict)
            Path(env["FRAMEAI_RUN_OUTPUTS"]).joinpath("result.txt").write_text(
                "fixture output\n", encoding="utf-8"
            )
        return subprocess.CompletedProcess([self.executable], self.returncode)


class FrameProviderIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.frame = runpy.run_path(str(FRAME_PATH))
        self.globals = self.frame["main"].__globals__
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.globals["ROOT"] = self.root
        self.globals["AUTOMATIONS"] = self.root / "automations"
        self.globals["SKILLS"] = self.root / "skills"

    def tearDown(self):
        self.tempdir.cleanup()

    def install_adapters(self, *, returncode: int = 0, write_output: bool = False):
        adapters = {
            name: FakeAdapter(name, returncode=returncode, write_output=write_output)
            for name in ("claude", "codex")
        }

        def get_provider(name: str):
            try:
                return adapters[name]
            except KeyError as exc:
                raise ValueError(
                    f"unsupported provider {name!r}; choose one of: claude, codex"
                ) from exc

        self.globals["get_provider"] = get_provider
        return adapters

    def make_skill(self, slug: str = "fixture") -> None:
        skill_dir = self.globals["SKILLS"] / slug
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# fixture\n", encoding="utf-8")

    def invoke(self, argv: list[str], env: dict[str, str] | None = None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.dict(os.environ, env or {}, clear=True):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = self.frame["main"](argv)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_add_routes_default_claude_and_explicit_codex(self):
        for provider in ("claude", "codex"):
            with self.subTest(provider=provider):
                adapters = self.install_adapters()
                slug = f"add-{provider}"
                argv = ["add", "fixture description", "--slug", slug]
                if provider == "codex":
                    argv += ["--provider", "codex"]

                result, stdout, _ = self.invoke(argv)

                self.assertEqual(result, 0)
                self.assertEqual(len(adapters[provider].calls), 1)
                self.assertEqual(len(adapters["codex" if provider == "claude" else "claude"].calls), 0)
                prompt, kwargs = adapters[provider].calls[0]
                self.assertIn(f"automations/{slug}/input.md", prompt)
                self.assertEqual(kwargs, {"cwd": self.root})
                self.assertIn(f"dispatching Fake {provider}", stdout)

    def test_refine_routes_default_claude_and_explicit_codex(self):
        self.make_skill()
        for provider in ("claude", "codex"):
            with self.subTest(provider=provider):
                adapters = self.install_adapters()
                argv = ["refine", "fixture", f"change via {provider}"]
                if provider == "codex":
                    argv += ["--provider", "codex"]

                result, _, _ = self.invoke(argv)

                self.assertEqual(result, 0)
                self.assertEqual(len(adapters[provider].calls), 1)
                prompt, kwargs = adapters[provider].calls[0]
                self.assertIn(f"change via {provider}", prompt)
                self.assertEqual(kwargs, {"cwd": self.root})

    def test_run_preserves_archive_streams_env_and_nonzero_exit_without_fallback(self):
        self.make_skill()
        adapters = self.install_adapters(returncode=19, write_output=True)

        with patch.object(self.globals["timestamp"], "__call__", wraps=self.globals["timestamp"]):
            # Patch the function's global directly because ``runpy`` returns the
            # actual globals mapping used by the loaded command functions.
            original_timestamp = self.globals["timestamp"]
            self.globals["timestamp"] = lambda: "2026-07-21T00-00-00"
            try:
                result, stdout, _ = self.invoke(
                    ["run", "--provider", "codex", "fixture", "input text"],
                    {"FRAMEAI_PROVIDER": "claude", "SAFE_FIXTURE": "1"},
                )
            finally:
                self.globals["timestamp"] = original_timestamp

        self.assertEqual(result, 19)
        self.assertEqual(len(adapters["codex"].calls), 1)
        self.assertEqual(len(adapters["claude"].calls), 0)
        prompt, kwargs = adapters["codex"].calls[0]
        run_dir = self.root / "automations/fixture/runs/2026-07-21T00-00-00"
        self.assertTrue((run_dir / "prompt.txt").is_file())
        self.assertEqual((run_dir / "prompt.txt").read_text(encoding="utf-8"), prompt)
        self.assertTrue((run_dir / "outputs/result.txt").is_file())
        log = (run_dir / "log.txt").read_text(encoding="utf-8")
        self.assertIn("FRAMEAI_RUN_MODE=cli", log)
        self.assertIn("--- fake codex stdout ---", log)
        self.assertEqual(kwargs["cwd"], self.root)
        self.assertEqual(kwargs["stderr"], subprocess.STDOUT)
        self.assertEqual(kwargs["env"]["FRAMEAI_RUN_TEXT"], "input text")
        self.assertEqual(kwargs["env"]["SAFE_FIXTURE"], "1")
        self.assertIn("1 output file(s)", stdout)

    def test_unknown_environment_provider_fails_before_add_scaffold_without_fallback(self):
        adapters = self.install_adapters()

        result, _, stderr = self.invoke(
            ["add", "must not scaffold", "--slug", "not-created"],
            {"FRAMEAI_PROVIDER": "invalid"},
        )

        self.assertEqual(result, 2)
        self.assertIn("unsupported provider 'invalid'", stderr)
        self.assertFalse((self.globals["AUTOMATIONS"] / "not-created").exists())
        self.assertEqual(adapters["claude"].calls, [])
        self.assertEqual(adapters["codex"].calls, [])


if __name__ == "__main__":
    unittest.main()
