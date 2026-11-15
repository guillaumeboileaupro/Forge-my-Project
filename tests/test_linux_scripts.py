import os
import signal
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def script_environment(python: str = sys.executable) -> dict[str, str]:
    environment = os.environ.copy()
    environment["FORGE_PYTHON"] = python
    return environment


class InstallerTests(unittest.TestCase):
    def test_installation_check_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix="clean forge install ") as directory:
            target = Path(directory)
            for name in ("installer.sh", "start.sh", "start.py", "server.py"):
                shutil.copy2(ROOT / name, target / name)
            shutil.copytree(ROOT / "scripts", target / "scripts")
            for _ in range(2):
                completed = subprocess.run(
                    [str(target / "installer.sh")],
                    cwd="/",
                    env=script_environment(),
                    text=True,
                    capture_output=True,
                    check=True,
                )
                self.assertIn("Forge-my-Project est pret", completed.stdout)
                self.assertIn("Aucun paquet, acces reseau ou privilege", completed.stdout)

    def test_incompatible_python_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_python = Path(directory) / "python-old"
            fake_python.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            fake_python.chmod(0o755)
            completed = subprocess.run(
                [str(ROOT / "installer.sh")],
                env=script_environment(str(fake_python)),
                text=True,
                capture_output=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Python 3.11+ executable", completed.stderr)

    def test_no_compatible_python_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory)
            for name in ("dirname", "uname"):
                executable = shutil.which(name)
                self.assertIsNotNone(executable)
                (tools / name).symlink_to(executable)
            environment = os.environ.copy()
            environment.pop("FORGE_PYTHON", None)
            environment["PATH"] = str(tools)
            completed = subprocess.run(
                [str(ROOT / "installer.sh")],
                env=environment,
                text=True,
                capture_output=True,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Python 3.11 ou plus recent est requis", completed.stderr)


class StartScriptTests(unittest.TestCase):
    def test_path_with_spaces_and_arguments_are_preserved(self):
        with tempfile.TemporaryDirectory(prefix="forge path with spaces ") as directory:
            target = Path(directory)
            shutil.copy2(ROOT / "start.sh", target / "start.sh")
            shutil.copytree(ROOT / "scripts", target / "scripts")
            (target / "start.py").write_text(
                "import json, pathlib, sys\n"
                "pathlib.Path(sys.argv[1]).write_text(json.dumps(sys.argv[2:]))\n",
                encoding="utf-8",
            )
            output = target / "arguments with spaces.json"
            subprocess.run(
                [str(target / "start.sh"), str(output), "one value", "two"],
                cwd="/",
                env=script_environment(),
                check=True,
            )
            self.assertEqual(output.read_text(encoding="utf-8"), '["one value", "two"]')

    def test_start_from_another_directory_skips_busy_port_and_stops(self):
        busy = socket.socket()
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        self.addCleanup(busy.close)
        first_port = busy.getsockname()[1]

        process = subprocess.Popen(
            [str(ROOT / "start.sh"), "--no-browser", "--port", str(first_port)],
            cwd="/",
            env=script_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        self.addCleanup(self._stop, process)

        selected_port = None
        deadline = time.monotonic() + 5
        while selected_port is None and time.monotonic() < deadline and process.poll() is None:
            for port in range(first_port + 1, min(first_port + 20, 65536)):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.1) as response:
                        if b"<title>Forge-my-Project</title>" in response.read(4096):
                            selected_port = port
                            break
                except OSError:
                    continue
            if selected_port is None:
                time.sleep(0.05)

        self.assertIsNotNone(selected_port, self._output(process))
        self.assertNotEqual(selected_port, first_port)
        self._stop(process)
        self.assertIsNotNone(process.returncode)

    @staticmethod
    def _output(process: subprocess.Popen[str]) -> str:
        if process.poll() is None or process.stdout is None:
            return ""
        return process.stdout.read()

    @staticmethod
    def _stop(process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout is not None and not process.stdout.closed:
            process.stdout.close()


if __name__ == "__main__":
    unittest.main()
