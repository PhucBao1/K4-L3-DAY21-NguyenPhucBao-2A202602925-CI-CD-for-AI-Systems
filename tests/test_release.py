import io
import json
from unittest.mock import Mock

from botocore.exceptions import ClientError
import pytest

from src.release import publish_candidate


@pytest.mark.parametrize("previous,new_f1,allowed", [
    (None, 0.7, True), (0.7, 0.7, True), (0.7, 0.8, True),
    (0.8, 0.7, False), (None, 0.64, False),
    (0.7, float("nan"), False), (float("nan"), 0.7, False),
])
def test_only_approved_candidates_are_published(previous, new_f1, allowed):
    s3 = Mock()
    if previous is None:
        s3.get_object.side_effect = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    else:
        s3.get_object.return_value = {"Body": io.BytesIO(json.dumps({"f1_score": previous}).encode())}
    if allowed:
        publish_candidate(s3, "test-bucket", {"f1_score": new_f1})
        s3.upload_file.assert_called_once_with("models/model.joblib", "test-bucket", "artifacts/current/model.joblib")
    else:
        with pytest.raises(ValueError):
            publish_candidate(s3, "test-bucket", {"f1_score": new_f1})
        s3.upload_file.assert_not_called()


def test_permission_error_is_not_treated_as_missing_baseline():
    s3 = Mock()
    s3.get_object.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
    with pytest.raises(ClientError):
        publish_candidate(s3, "test-bucket", {"f1_score": 0.8})
    s3.upload_file.assert_not_called()
