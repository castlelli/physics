"""The site's model.js reproduces modelo.py on the golden fixture to 1e-12 (needs Node; skipped without it)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from codigo.site import SITE_DIR, export_site

HERE = Path(__file__).resolve().parent


def find_node() -> str | None:
    found = shutil.which("node")
    if found:
        return found
    versions = sorted((Path.home() / ".nvm" / "versions" / "node").glob("v*/bin/node"))
    return str(versions[-1]) if versions else None


@pytest.mark.skipif(find_node() is None, reason="Node não encontrado: a paridade com o site não foi testada")
def test_site_model_matches_python_on_the_golden_fixture():
    export_site(SITE_DIR)  # the fixture the site ships is the one this Python writes
    proc = subprocess.run([find_node(), str(HERE / "paridade.mjs")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
