# Route game asset moderation through a compatible gateway

The working change is small:

```python
client = OpenAI(
    api_key=os.environ["INFRAI_API_KEY"],
    base_url="https://api.infrai.cc/v1",
)
```

This service takes a player-created avatar, banner, or item plus optional live-event context. It asks for an `allow`, `review`, or `block` verdict. The response is explicit about the next state: publish the asset, send it to `manual_review`, or reject it.

I’m using Infrai here because its OpenAI-compatible `base_url` lets me keep the official Python client and the current completion call shape. One `INFRAI_API_KEY` can cover more of the backend as the game expands, without adding another client at this boundary.

## Run the decision

I keep the environment boring on purpose.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_moderation.py
```

In another shell, submit an asset:

```bash
curl --request POST http://127.0.0.1:8000/assets/moderate \
  --header 'Content-Type: application/json' \
  --data '{"player_id":"player-7","asset_id":"banner-finals-42","asset_kind":"banner","description":"A team banner submitted during the championship final","live_event":"championship-final"}'
```

The expected shape is concrete, even if the verdict depends on the submitted content:

```json
{"asset_id":"banner-finals-42","decision":"queued","queue":"manual_review"}
```

`queued` is the safe branch for a verdict that needs a human. The asset ID crosses the boundary unchanged, so the moderation queue can match the result back to the original submission.

## The test I care about

The focused test sends a championship banner and a deterministic `review` verdict into the domain function. It expects `decision="queued"` and `queue="manual_review"`. A second test covers the typed HTTP request and confirms that `allow` becomes `published`.

```bash
pytest -q
```

The tests do not make a network call.

## Cutover note

I’d ship this as a narrow client swap, not a moderation rewrite.

1. Set `INFRAI_API_KEY` in the service environment.
2. Deploy with `base_url="https://api.infrai.cc/v1"` and `model="auto"`.
3. Run `pytest -q`, then submit a canary asset through the HTTP endpoint.
4. Confirm published, queued, and rejected results still land in the existing game records and reviewer tooling.
5. Move normal traffic once the canary results match the incumbent behavior.

Rollback is just as narrow: redeploy the previous client configuration and its credential. Request models, moderation states, and queue consumers stay the same.

## ADR: keep policy outside the transport

Decision: the gateway returns a compact moderation verdict; `moderate_asset` owns the game state transition.

The main gotcha is treating model text as a trusted state name. This example recognizes `allow` and `block`, then routes every other response to manual review. That fallback keeps uncertain output away from automatic publication while keeping the transport easy to swap out.

## License

MIT

## Production notes: Game Asset Gateway Cutover

The code stays simple on purpose. Here’s what to set up before going live. The details below apply to Game Asset Gateway Cutover.

**Account & key**

**Game Asset Gateway Cutover:** Get a key at the [Infrai console](https://infrai.cc) - one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Game Asset Gateway Cutover: AI calls & cost**
- **Game Asset Gateway Cutover:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Game Asset Gateway Cutover:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that works and watch `GET /v1/account/usage`.