import os
import json
import numpy as np
import pandas as pd
import pytest
import mlflow
import joblib
from sklearn.metrics import f1_score
from src.train import train, select_threshold


FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


@pytest.fixture(autouse=True)
def isolated_outputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mlflow.set_tracking_uri((tmp_path / "mlruns").as_uri())


def _make_temp_data(tmp_path):
    """
    Tao dataset nho voi cung schema Adult de su dung trong test.

    pytest cung cap `tmp_path` la mot thu muc tam thoi, tu dong xoa sau khi test ket thuc.
    Ham nay dung du lieu ngau nhien nen khong can ket noi cloud storage hay tai file CSV thuc.
    """
    rng = np.random.default_rng(0)
    n = 200

    X = rng.random((n, len(FEATURE_NAMES)))
    # Bai toan nay chi co HAI lop (0 va 1), nen can tren la 2.
    y = rng.integers(0, 2, size=n)

    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df["target"] = y

    # 160 dong dau lam tap huan luyen, 40 dong cuoi lam tap holdout
    train_path = str(tmp_path / "train.csv")
    eval_path = str(tmp_path / "holdout.csv")
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)

    return train_path, eval_path


def test_train_returns_float(tmp_path):
    """Kiem tra ham train() tra ve mot so thuc nam trong [0.0, 1.0]."""
    train_path, eval_path = _make_temp_data(tmp_path)

    f1 = train(
        {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    assert isinstance(f1, float)
    assert 0.0 <= f1 <= 1.0


def test_report_file_created(tmp_path, capsys):
    """Kiem tra file outputs/report.json duoc tao sau khi huan luyen."""
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    assert os.path.exists("outputs/report.json")
    with open("outputs/report.json") as f:
        report = json.load(f)
    assert "f1_score" in report
    assert "accuracy" in report
    assert report["f1_score"] >= report["default_f1_score"]
    assert 0.1 <= report["best_threshold"] <= 0.9
    artifact = joblib.load("models/model.joblib")
    assert artifact["threshold"] == report["best_threshold"]
    evaluation = pd.read_csv(eval_path)
    probabilities = artifact["model"].predict_proba(evaluation.drop(columns="target"))[:, 1]
    assert report["f1_score"] == f1_score(evaluation["target"], probabilities >= artifact["threshold"])
    expected_ratio = float(pd.read_csv(train_path)["target"].eq(1).mean())
    assert report["positive_ratio"] == expected_ratio
    assert "WARNING: positive class ratio" in capsys.readouterr().out
    detail = (tmp_path / "outputs" / "detail.txt").read_text(encoding="utf-8")
    assert "Confusion matrix" in detail
    assert "precision" in detail and "recall" in detail
    assert "thu_nhap_thap" in detail and "thu_nhap_cao" in detail


def test_model_file_created(tmp_path):
    """Kiem tra file models/model.joblib duoc tao sau khi huan luyen."""
    train_path, eval_path = _make_temp_data(tmp_path)
    train(
        {"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2},
        data_path=train_path,
        eval_path=eval_path,
    )

    assert os.path.exists("models/model.joblib")


def test_reference_distribution_does_not_warn(tmp_path, capsys):
    train_path, eval_path = _make_temp_data(tmp_path)
    data = pd.read_csv(train_path)
    data["target"] = [1] * 40 + [0] * 120
    data.to_csv(train_path, index=False)
    train({"n_estimators": 10, "learning_rate": 0.1, "max_depth": 2}, train_path, eval_path)
    assert "WARNING: positive class ratio" not in capsys.readouterr().out


def test_threshold_search_improves_f1_and_prefers_default_on_tie():
    threshold, f1 = select_threshold([0, 0, 1, 1], np.array([0.1, 0.2, 0.35, 0.4]))
    assert threshold == 0.35
    assert f1 == 1.0
    assert select_threshold([0, 1], np.array([0.0, 1.0])) == (0.5, 1.0)
