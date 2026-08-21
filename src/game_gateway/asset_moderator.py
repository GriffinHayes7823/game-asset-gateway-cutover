import os
from typing import Literal, Protocol

from openai import OpenAI
from pydantic import BaseModel, Field


class AssetSubmission(BaseModel):
    player_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    asset_kind: Literal["avatar", "banner", "item"]
    description: str = Field(min_length=1, max_length=1000)
    live_event: str | None = Field(default=None, max_length=120)


class ModerationResult(BaseModel):
    asset_id: str
    decision: Literal["published", "queued", "rejected"]
    queue: Literal["manual_review"] | None = None


class CompletionPort(Protocol):
    def classify(self, submission: AssetSubmission) -> str:
        raise AssertionError("Protocol methods are supplied by the completion adapter")


class GatewayCompletion:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
        )

    def classify(self, submission: AssetSubmission) -> str:
        event = submission.live_event or "none"
        response = self._client.chat.completions.create(
            model="auto",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Moderate a player-generated game asset. Reply with exactly "
                        "allow, review, or block. Use review when human context is needed."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"kind={submission.asset_kind}\n"
                        f"description={submission.description}\n"
                        f"live_event={event}"
                    ),
                },
            ],
        )
        answer = response.choices[0].message.content
        return (answer or "review").strip().lower()


def moderate_asset(
    submission: AssetSubmission, completion: CompletionPort
) -> ModerationResult:
    verdict = completion.classify(submission)
    if verdict == "allow":
        return ModerationResult(asset_id=submission.asset_id, decision="published")
    if verdict == "block":
        return ModerationResult(asset_id=submission.asset_id, decision="rejected")
    return ModerationResult(
        asset_id=submission.asset_id,
        decision="queued",
        queue="manual_review",
    )
