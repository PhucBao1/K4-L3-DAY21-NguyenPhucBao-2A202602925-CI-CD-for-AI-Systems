"""Verify the actual workflow gate and placement of the S3 publication step."""
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/cicd.yml"


@pytest.mark.parametrize("f1,passes", [(0.64, False), (0.65, True), (0.74, True)])
def test_quality_gate(f1, passes):
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    script = jobs["quality-gate"]["steps"][0]["run"]
    code = script.split("\n", 1)[1].rsplit("PYEOF", 1)[0]
    code = code.replace("${{ needs.train.outputs.f1 }}", str(f1))
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert (result.returncode == 0) is passes, result.stderr
    assert jobs["release"]["needs"] == "quality-gate"


def test_current_model_is_only_uploaded_after_gate():
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    assert all("artifacts/current/" not in step.get("run", "") for step in jobs["train"]["steps"])
    release_steps = jobs["release"]["steps"]
    upload = next(i for i, step in enumerate(release_steps) if "python src/release.py" in step.get("run", ""))
    deploy = next(i for i, step in enumerate(release_steps) if step.get("name") == "SSH deploy to VM")
    baseline = next(i for i, step in enumerate(release_steps) if "artifacts/current/report.json" in step.get("run", ""))
    assert upload < deploy
    assert deploy < baseline
