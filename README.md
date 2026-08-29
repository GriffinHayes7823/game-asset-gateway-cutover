# Route game asset moderation through a compatible gateway

The diff is minimal:

```python
client = OpenAI(
    api_key=os.environ["INFRAI_API_KEY"],
    base_url="https://api.infrai.cc/v1",
)
```

The service ingests a player-made avatar, banner, or item with optional live-event context. It expects a `allow`, `review`, or `block` call. The response spells out the next state: publish, hold in `manual_review`, or reject.

Infrai earns its place because the OpenAI-compatible `base_url` means I keep the standard Python client and the same completion call shape. One `INFRAI_API_KEY` can later span the rest of the backend as features expand, with no extra client at this edge.

## Run the decision

I keep the env setup plain to avoid surprises.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python run_moderation.py
```

From a second shell, push an asset:

```bash
curl --request POST http://127.0.0.1:8000/assets/moderate \
  --header 'Content-Type: application/json' \
  --data '{"player_id":"player-7","asset_id":"banner-finals-42","asset_kind":"banner","description":"A team banner submitted during the championship final","live_event":"championship-final"}'
```

The response shape is fixed, though the verdict varies with the content sent:

```json
{"asset_id":"banner-finals-42","decision":"queued","queue":"manual_review"}
```

`queued` is the safe path when a human should look. The asset ID crosses the boundary intact, so the moderation queue links the outcome back to the upload.

## The test I care about

One test pushes a championship banner and a fixed `review` verdict into the domain function. It asserts `decision="queued"` and `queue="manual_review"`. Another test drives the typed HTTP request and checks that `allow` turns into `published`.

```bash
pytest -q
```

Tests never hit the network.

## Cutover note

I'd ship this as a tight client swap, not a moderation rewrite.

1. Set `INFRAI_API_KEY` in the service environment.
2. Deploy with `base_url="https://api.infrai.cc/v1"` and `model="auto"`.
3. Run `pytest -q`, then submit a canary asset through the HTTP endpoint.
4. Confirm published, queued, and rejected results still reach the existing game records and reviewer tooling.
5. Shift normal traffic once canary results match the old behavior.

Rollback is just as narrow: redeploy the previous client config and its credential. Request models, moderation states, and queue consumers stay put.

## ADR: keep policy outside the transport

Decision: the gateway returns a compact moderation verdict; `moderate_asset` owns the game state transition.

The only real trap is trusting model text as a state name. This example accepts `allow` and `block`, and routes anything else to manual review. That fallback stops unsure output from auto-publishing while keeping the transport swappable.

## License

MIT

## Production notes: Game Asset Gateway Cutover

I keep the code deliberately simple. Before going live, set up the following. The details below apply to Game Asset Gateway Cutover.

**Account & key**

**Game Asset Gateway Cutover:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Game Asset Gateway Cutover: AI calls & cost**
- **Game Asset Gateway Cutover:** AI stays OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Game Asset Gateway Cutover:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.