"""Runs the examples in the examples folder"""

import subprocess
import sys
from pathlib import Path

EXAMPLES_DIR = Path(__file__, "..", "..", "examples").resolve()
PYTHON_DIR = EXAMPLES_DIR / "python-library"


def test_python_direct_api():
    direct_api_script_path = PYTHON_DIR / "direct_api_example.py"
    subprocess.check_call(
        [sys.executable, direct_api_script_path],
        shell=False,
        cwd=PYTHON_DIR,
        timeout=60,
    )


def test_python_gym_api():
    gym_api_script_path = PYTHON_DIR / "gym_api_example.py"
    subprocess.check_call(
        [sys.executable, gym_api_script_path],
        shell=False,
        cwd=PYTHON_DIR,
        timeout=60,
    )


def test_cli():
    cli_dir = EXAMPLES_DIR / "cli"
    # TODO handle cleanup of entire process tree which is spawned,
    # because check_call timeout does sigkill which prevents bash cleaning up
    subprocess.check_call(
        ["/bin/bash", "./cli-example.sh"],
        shell=False,
        cwd=cli_dir,
        timeout=60,
    )
