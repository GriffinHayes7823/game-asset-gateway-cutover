from fastapi.testclient import TestClient

from game_gateway.asset_moderator import AssetSubmission, moderate_asset
from game_gateway.moderation_service import gateway_completion, service


class FixedCompletion:
    def __init__(self, verdict: str) -> None:
        self.verdict = verdict

    def classify(self, submission: AssetSubmission) -> str:
        return self.verdict


def test_review_verdict_places_live_event_asset_in_manual_queue() -> None:
    submission = AssetSubmission(
        player_id="player-7",
        asset_id="banner-finals-42",
        asset_kind="banner",
        description="A team banner submitted during the championship final",
        live_event="championship-final",
    )

    result = moderate_asset(submission, FixedCompletion("review"))

    assert result.model_dump() == {
        "asset_id": "banner-finals-42",
        "decision": "queued",
        "queue": "manual_review",
    }


def test_typed_http_boundary_returns_publish_decision() -> None:
    service.dependency_overrides[gateway_completion] = lambda: FixedCompletion("allow")
    try:
        response = TestClient(service).post(
            "/assets/moderate",
            json={
                "player_id": "player-9",
                "asset_id": "avatar-9",
                "asset_kind": "avatar",
                "description": "A silver space explorer",
            },
        )
    finally:
        service.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "asset_id": "avatar-9",
        "decision": "published",
        "queue": None,
    }
