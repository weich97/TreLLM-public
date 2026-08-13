# Security Policy

TreLLM is an LLM-driven trading audit and live-readiness control system.
TradeArena is the public leaderboard and benchmark-card surface inside TreLLM.
It does not execute live trades by default, and public examples are offline,
paper/sandbox, dry-run, or human-review oriented.

## Please Do Not Submit

- API keys, broker credentials, or account tokens.
- Raw provider prompt/response caches.
- Private portfolios, account statements, or personally identifiable data.
- Live-order adapters that submit trades without explicit sandboxing, human
  approval, order limits, reconciliation, and a kill switch.
- `.env` files, cookies, private notebook outputs, or local broker/account
  exports.

## Reporting Security Issues

For credential leakage, unsafe execution boundaries, prompt/cache exposure, or
other security-sensitive issues, email:

```text
weich97@vt.edu
```

Please include a minimal reproduction and avoid publishing sensitive details in
public issues until the report has been triaged.

## Safe-Execution Boundary

Adapters that touch brokers, exchanges, or portfolio data must default to one of
these modes:

- offline export,
- paper trading,
- redacted manifest generation,
- or human-approved review.

Live execution is out of scope for the public TradeArena leaderboard path unless
it is explicitly human-approved, sandbox-tested, documented as unsafe for
unattended use, and implemented behind the broker adapter contract.

## Advanced Integrations

Provider and data integrations are opt-in. A safe run should satisfy all of the
following:

- keys are read from environment variables or an OS secret manager, never from
  committed files or command-line flags;
- raw LLM caches stay under ignored local paths such as `data/llm_cache/` or
  `outputs/`;
- public artifacts use redacted benchmark submissions or cache manifests;
- Yahoo Finance, AkShare, and other market-data downloads record source,
  frequency, symbol universe, timestamp policy, and adjustment assumptions;
- broker-facing examples remain offline export, dry-run, paper sandbox, or
  human-approved by default;
- errors from provider APIs omit response bodies when those bodies may contain
  sensitive details.

See [`docs/advanced_integrations_security.md`](docs/advanced_integrations_security.md),
[`docs/live_trading_readiness.md`](docs/live_trading_readiness.md), and
[`docs/broker_adapter_contract.md`](docs/broker_adapter_contract.md) for the
operational checklist.

## If A Secret Is Exposed

1. Revoke or rotate the provider or broker credential immediately.
2. Remove local cache files that contain the exposed value.
3. Do not paste the secret into a public issue. Report privately using the
   address above.
4. If the secret reached Git history, treat it as compromised even after the
   file is deleted.
