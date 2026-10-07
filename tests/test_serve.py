from pathlib import Path
import runpy
from unittest.mock import Mock, patch

from fastapi import HTTPException
import numpy as np
import pytest


@pytest.mark.parametrize("bundled,expected", [(True, 1), (False, 0)])
def test_api_uses_saved_threshold_and_accepts_legacy_models(tmp_path, monkeypatch, bundled, expected):
    model = Mock()
    model.predict_proba.return_value = np.array([[0.6, 0.4]])
    artifact = {"model": model, "threshold": 0.35} if bundled else model
    monkeypatch.setenv("ARTIFACT_BUCKET", "test-bucket")
    with patch("boto3.client"), patch("joblib.load", return_value=artifact), \
         patch("os.path.expanduser", return_value=str(tmp_path / "model.joblib")):
        module = runpy.run_path(str(Path(__file__).resolve().parents[1] / "src/serve.py"))
    assert module["healthz"]() == {"status": "ok"}
    request = module["ScoreRequest"](features=[28, 2, 14, 2, 11, 0, 1, 0, 0, 45])
    assert module["score"](request) == {"prediction": expected, "label": "thu_nhap_cao" if expected else "thu_nhap_thap"}
    with pytest.raises(HTTPException) as error:
        module["score"](module["ScoreRequest"](features=[1]))
    assert error.value.status_code == 400
