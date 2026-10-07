"""Reject a lower-F1 candidate before publishing its model to S3."""
import json
import math
import os

import boto3
from botocore.exceptions import ClientError


REPORT_KEY = "artifacts/current/report.json"


def check_release(candidate, previous):
    new_f1 = float(candidate["f1_score"])
    if not math.isfinite(new_f1) or not 0.65 <= new_f1 <= 1:
        raise ValueError(f"Rejected candidate F1: {new_f1}")
    if previous is None:
        print(f"No previous report: first tracked release, candidate F1={new_f1:.4f}")
        return
    old_f1 = float(previous["f1_score"])
    if not math.isfinite(old_f1) or not 0 <= old_f1 <= 1:
        raise ValueError(f"Invalid previous F1: {old_f1}")
    print(f"Release comparison: previous F1={old_f1:.4f}, candidate F1={new_f1:.4f}")
    if new_f1 < old_f1:
        raise ValueError("Release blocked: candidate F1 is lower than the deployed model.")


def publish_candidate(s3, bucket, candidate):
    try:
        response = s3.get_object(Bucket=bucket, Key=REPORT_KEY)
    except ClientError as error:
        # Only an absent baseline is allowed; authentication/network errors fail closed.
        if error.response["Error"]["Code"] not in ("NoSuchKey", "404"):
            raise
        previous = None
    else:
        previous = json.load(response["Body"])
    check_release(candidate, previous)
    s3.upload_file("models/model.joblib", bucket, "artifacts/current/model.joblib")
    print(f"Approved model uploaded to s3://{bucket}/artifacts/current/model.joblib")


if __name__ == "__main__":
    with open("outputs/report.json", encoding="utf-8") as file:
        candidate = json.load(file)
    publish_candidate(boto3.client("s3"), os.environ["ARTIFACT_BUCKET"], candidate)
