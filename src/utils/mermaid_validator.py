"""Validate Mermaid diagram syntax by compiling with mermaid-cli (mmdc). Returns parse errors for LLM retry."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def validate_mermaid(code: str) -> tuple[bool, str]:
    """
    Try to compile Mermaid code with mmdc. Returns (True, "") if valid or if mmdc is not available.
    Returns (False, error_message) if mmdc runs and reports a parse error (stderr or generic message).
    """
    if not code or not code.strip():
        return False, "Diagram code is empty."

    # Check if npx is available (Node.js)
    npx = shutil.which("npx")
    if not npx:
        return True, ""  # Skip validation; don't fail the pipeline

    with tempfile.TemporaryDirectory(prefix="mermaid_validate_") as tmpdir:
        tmp = Path(tmpdir)
        input_mmd = tmp / "diagram.mmd"
        output_svg = tmp / "out.svg"
        input_mmd.write_text(code, encoding="utf-8")
        try:
            # npx runs the package's binary (mmdc); args are -i and -o
            result = subprocess.run(
                [
                    npx,
                    "-y",
                    "@mermaid-js/mermaid-cli@latest",
                    "-i",
                    str(input_mmd),
                    "-o",
                    str(output_svg),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return True, ""  # Don't fail on env issues

        if result.returncode == 0:
            return True, ""

        # mmdc failed: use stderr if present, else a generic message
        err = (result.stderr or result.stdout or "").strip()
        if not err:
            err = "Mermaid parser reported a syntax error (no details from mmdc)."
        return False, err
