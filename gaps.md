  Must-fix before real traffic:

  ┌────────────────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                Gap                 │                                                          Why it matters                                                           │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No PostgreSQL in CI                │ Tests only run against SQLite — async behavior, JSON columns, and constraint handling differ. Need a Postgres test job in GitHub  │
  │                                    │ Actions                                                                                                                           │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No integration test against a real │ All A2A tests mock the provider side. Need at least one test that hits a demo agent                                               │
  │  agent                             │                                                                                                                                   │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Secrets in .env not validated at   │ DATABASE_URL pointing at SQLite in prod would silently work but lose data on restart                                              │
  │ startup                            │                                                                                                                                   │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No HTTPS enforcement               │ The backend trusts X-Forwarded-Proto but doesn't reject plain HTTP in prod                                                        │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Push notifier runs in create_task  │ If the callback is slow (even with timeout), it blocks the response. Should be a background task queue (Celery, arq, or at        │
  │                                    │ minimum asyncio.create_task with error handling)                                                                                  │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No logging/observability           │ No structured logging, no request tracing, no error reporting (Sentry, etc.). When something breaks in prod you'll be blind       │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No container/Dockerfile            │ The README mentions Docker but there's no Dockerfile in the repo                                                                  │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Rate limiter is in-memory          │ Fine for a single instance, but if you scale to 2+ Cloud Run instances each has its own counter. Need Redis-backed limiter for    │
  │                                    │ real scale                                                                                                                        │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ MCP resources bypass auth          │ The /api/v1/mcp-resources/* endpoints are public — anyone can enumerate your agent registry                                       │
  ├────────────────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No input sanitization on task      │ messages and artifacts are stored as raw JSON. An attacker could store multi-MB payloads                                          │
  │ messages                           │                                                                                                                                   │
  └────────────────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Should-fix before launch:

  ┌─────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │               Gap               │                                                           Impact                                                            │
  ├─────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Firebase token refresh          │ The __auth_token cookie has a 1-hour max-age but Firebase tokens expire in 1 hour too — no auto-refresh logic in middleware │
  ├─────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No email verification           │ Users can register with any email address                                                                                   │
  ├─────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No API key rotation             │ Once generated, API keys can't be revoked without DB access                                                                 │
  ├─────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Desktop updater pubkey is empty │ Auto-updater won't work without a signing key                                                                               │
  ├─────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No backup/recovery plan         │ Single Neon Postgres instance, no documented backup procedure                                                               │
  ├─────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ No load testing                 │ Unknown how many concurrent SSE streams or tasks the system handles                                                         │
  └─────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Verdict: You're at roughly ~80% now (up from ~65% before the remediation). The security surface is much better, but you need observability, a Dockerfile, Postgres CI tests,
  and background task processing before handling real users. For a demo or internal pilot — it's ready. For public production traffic — give it another pass on the items
  above.
