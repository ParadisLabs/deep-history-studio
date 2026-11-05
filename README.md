
## OpsHub

One shared module, `hub.py`, feeds and is triggered by OpsHub in every studio.

**Feed.** `content.episode_ready`, `content.series_state` and
`content.series_finished` are POSTed to `$HUB_URL/ingest` (`schema_version: 1`),
signed with `x-hub-signature-256` using `HUB_WEBHOOK_SECRET`. If the hub only
exposes the older unsigned route, the same event is retried against
`$OPSHUB_URL/emit`, so both hub generations keep working. Emitting is never
fatal: a broken hub cannot kill a render.

**Trigger.** `repository_dispatch` with type `opshub.produce` (or `opshub.run`).
OpsHub sends it with any token that has `contents: write` here. The
`client_payload` supports:

| key | meaning |
|---|---|
| `topic` | free-text brief for the next episode (`new_series` ignores it for a fresh arc) |
| `new_series` | `true` starts a brand-new arc instead of continuing the current one |
| `max_episodes` | override how long the arc runs |
| `reason` | free text, echoed into the run log |

Telegram needs no new bot: the same `TELEGRAM_BOT_TOKEN` works everywhere, only
`TELEGRAM_CHAT_ID` changes per studio.

```bash
curl -X POST https://api.github.com/repos/<owner>/<repo>/dispatches \
  -H "Authorization: Bearer $OPSHUB_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d '{"event_type":"opshub.produce","client_payload":{"topic":"","new_series":false,"reason":"opshub nightly"}}'
```


## Research sources

The researcher combines Wikipedia article extracts with free Library of Congress JSON catalog searches. LOC records are stored with their record URL, date, contributor and rights statement when supplied. Catalog descriptions are treated as metadata/corroboration, not as a substitute for full primary-source text or proof of every historical claim. The LOC connector requires no API key. Future connectors such as Smithsonian Open Access and Europeana should be enabled only after their free API keys are created and each asset's reuse rights are checked.


## Research APIs

Research digests combine Wikipedia article extracts with the free Library of Congress JSON catalog and Crossref's public scholarly metadata API. Neither connector requires a paid plan or API key. LOC records are catalog metadata; Crossref records may include publisher-supplied abstracts and DOI links. Both are labelled by source type and evidence level. Treat them as corroborating leads, verify major claims against primary sources, and preserve attribution/rights notes. Crossref abstracts remain subject to publisher rights.

## Shared image quota

Cloudflare image calls are admitted through OpsHub's signed `/ai-usage/reserve` endpoint. The shared UTC-day limits are 24 calls total and 10 per studio. This counts requests, not neurons, and cannot account for other Cloudflare workloads. If the ledger is missing, unavailable, or at its cap, the studio skips Cloudflare and uses its keyless Pollinations fallback. Existing `HUB_URL` and `HUB_WEBHOOK_SECRET` Actions secrets are required; no new secret is introduced. Deploy the OpsHub upgrade before merging/enabling this studio change.
