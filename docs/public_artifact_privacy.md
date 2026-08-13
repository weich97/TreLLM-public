# Public Artifact Privacy

TreLLM separates local debugging records from public TradeArena leaderboard
artifacts. This boundary is enforced in code and CI, not only by contributor
convention.

| Mode | Intended location | Behavior |
| --- | --- | --- |
| `private_debug` | ignored local caches such as `data/llm_cache/*.jsonl` | May retain raw prompts, raw provider responses, provider metadata, and local debugging context. |
| `public_artifact` | trajectories, manifests, dashboards, reports, and redacted leaderboard submissions | Keeps prompt and response hashes, provider/model/version fields, structured signals or weights, and redacted rationale text. Raw prompts, raw responses, credentials, emails, and account-like fields are not allowed. |

`Trajectory.to_dict()` and `write_json()` default to `public_artifact`. Code that
needs raw provider text should keep it in ignored local cache files and publish a
redacted manifest instead.

CI runs:

```bash
python scripts/scan_public_artifacts.py outputs docs/results examples/benchmark_submissions
```

The scan fails if public artifacts contain raw prompt/response fields,
Authorization headers, API-key-like strings, email addresses, or account-like
identifiers.
