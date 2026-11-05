
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
