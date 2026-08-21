from fastapi import Depends, FastAPI, HTTPException
from openai import APIStatusError

from .asset_moderator import (
    AssetSubmission,
    CompletionPort,
    GatewayCompletion,
    ModerationResult,
    moderate_asset,
)

service = FastAPI(title="Game asset moderation")


def gateway_completion() -> CompletionPort:
    return GatewayCompletion()


@service.post("/assets/moderate", response_model=ModerationResult)
def submit_asset(
    submission: AssetSubmission,
    completion: CompletionPort = Depends(gateway_completion),
) -> ModerationResult:
    try:
        return moderate_asset(submission, completion)
    except APIStatusError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=caller_status, detail=exc.message) from exc
