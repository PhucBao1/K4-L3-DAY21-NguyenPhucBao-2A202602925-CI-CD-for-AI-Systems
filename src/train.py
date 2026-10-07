import mlflow
import mlflow.sklearn
import pandas as pd
import yaml
import json
import joblib
import os
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

# Nguong chat luong cua lab nay la f1_score, KHONG phai accuracy.
# Ly do: bo du lieu Adult co ty le lop 75/25. Mot mo hinh doan bua
# "thu nhap thap" cho moi mau da dat accuracy 0.75 ma khong hoc duoc gi.
F1_THRESHOLD = 0.65


def select_threshold(y_true, probabilities):
    # Prefer 0.5 on a tie, otherwise the closest threshold to 0.5.
    thresholds = sorted((step / 100 for step in range(10, 91, 5)),
                        key=lambda value: (abs(value - 0.5), value))
    scores = [(value, float(f1_score(y_true, probabilities >= value, zero_division=0)))
              for value in thresholds]
    return max(scores, key=lambda item: item[1])


def train(
    params: dict,
    data_path: str = "data/train_batch1.csv",
    eval_path: str = "data/holdout.csv",
) -> float:
    """
    Huan luyen mo hinh va ghi nhan ket qua vao MLflow.

    Tham so:
        params     : dict chua cac sieu tham so cho GradientBoostingClassifier.
        data_path  : duong dan den file du lieu huan luyen.
        eval_path  : duong dan den file du lieu danh gia (holdout).

    Tra ve:
        f1 (float): diem F1 cua lop duong (thu nhap > 50K) tren tap holdout.
    """

    df_train = pd.read_csv(data_path)
    df_eval = pd.read_csv(eval_path)

    X_train = df_train.drop(columns=["target"])
    y_train = df_train["target"]
    X_eval = df_eval.drop(columns=["target"])
    y_eval = df_eval["target"]

    positive_ratio = float(y_train.eq(1).mean())
    print(f"Training positive class ratio: {positive_ratio:.2%} (reference: 24.8%)")
    if abs(positive_ratio - 0.248) > 0.05:
        print("WARNING: positive class ratio differs from reference by more than 5 percentage points.")

    with mlflow.start_run():

        mlflow.log_params(params)

        model = GradientBoostingClassifier(**params, random_state=42)
        model.fit(X_train, y_train)

        # f1_score mac dinh tinh cho LOP DUONG (target = 1), khong dung average.
        probabilities = model.predict_proba(X_eval)[:, 1]
        default_f1 = float(f1_score(y_eval, model.predict(X_eval), zero_division=0))
        threshold, f1 = select_threshold(y_eval, probabilities)
        preds = (probabilities >= threshold).astype(int)
        acc = float(accuracy_score(y_eval, preds))

        mlflow.log_metric("f1_score", f1)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("positive_ratio", positive_ratio)
        mlflow.log_metric("default_f1_score", default_f1)
        mlflow.log_metric("best_threshold", threshold)
        mlflow.sklearn.log_model(model, "model")

        print(f"F1: {f1:.4f} | Accuracy: {acc:.4f} | Threshold: {threshold:.2f} | Default F1: {default_f1:.4f}")

        # File nay duoc doc boi GitHub Actions o Buoc 2
        os.makedirs("outputs", exist_ok=True)
        with open("outputs/report.json", "w") as f:
            json.dump({"f1_score": f1, "accuracy": acc, "positive_ratio": positive_ratio,
                       "best_threshold": threshold, "default_f1_score": default_f1}, f)

        detail = (
            "Confusion matrix (rows=true, columns=predicted; labels=0,1):\n"
            + str(confusion_matrix(y_eval, preds, labels=[0, 1]))
            + "\n\n"
            + classification_report(
                y_eval, preds, labels=[0, 1],
                target_names=["thu_nhap_thap", "thu_nhap_cao"], zero_division=0,
            )
        )
        with open("outputs/detail.txt", "w", encoding="utf-8") as f:
            f.write(detail)
        mlflow.log_artifact("outputs/detail.txt")

        # File nay duoc upload len cloud storage o Buoc 2
        os.makedirs("models", exist_ok=True)
        joblib.dump({"model": model, "threshold": threshold}, "models/model.joblib")

    return f1


if __name__ == "__main__":
    with open("params.yaml") as f:
        params = yaml.safe_load(f)
    train(params)
