# WP0 Code Review (Platform EM, read-only)

Date: 2026-11-03
Scope: `src/jobai/llm/**`, `src/jobai/config.py`, `src/jobai/db.py`, `src/jobai/cli.py`, `migrations/0001_init.sql`, `tests/**`, `pyproject.toml`, `.gitignore`, `.env.example`
Spec: `docs/office/tickets/WP0.md`
Method: Read/Grep only. No installs, no test runs, no network. Findings are from reading the code; nothing was executed.

## Verdict: APPROVE-WITH-FIXES

No P0. Fix all P1 items before any WP calls `Gateway.complete` (WP1+). The cap and redaction core is sound in its main paths: reservation happens before the call, it runs under `BEGIN IMMEDIATE`, money is integer micro-USD with ceiling rounding, and the logs carry no prompts or completions.

---

## P0 (blocks merge)

None.

---

## P1 (fix before first real caller)

### P1-1. Retries are outside the reservation (spend can exceed the cap)
- `src/jobai/llm/gateway.py:87-95` reserves worst case for ONE attempt.
- `src/jobai/llm/providers/openai_provider.py:55-66` can make up to `max_attempts=4` HTTP requests inside that single reservation. A timed-out request that the server still bills, followed by retries, costs up to 4x the reserved amount.
- Fix: multiply the reservation by `max_attempts` (or pass the attempt count into `pricing.worst_case_micro`), or count each attempt as its own reservation in the provider via a callback. Add a test where the fake fails with a retryable error after billing and assert the ledger covers all attempts.

### P1-2. Schema tokens and message overhead are not in the worst-case estimate
- `src/jobai/llm/gateway.py:85`: `est_in = sum(len(m["content"]) for m in sent) // 3 + 1`.
- The JSON schema sent as `response_format` (`openai_provider.py:49-53`) is billed as prompt tokens, and it is not counted. Per-message role and framing overhead is not counted either.
- Large schemas can push the actual `in_tokens` well above the reservation, and the cap is then breached by the overrun. `settle` (`caps.py:83-94`) never re-checks the cap.
- Fix: include `len(json.dumps(schema))` and a per-message overhead (for example 8 tokens per message) in `est_in`, and add a safety margin. Add a test that a large schema is counted.

### P1-3. `json.loads` failures escape the ladder and break structured output
- `src/jobai/llm/gateway.py:112`: `json.loads(text)` runs outside any handler. A refusal gives `content=None` (`openai_provider.py:72` turns it into `""`), and a `finish_reason=length` truncation at 1024 tokens gives invalid JSON. Either one raises `json.JSONDecodeError`, which is not an `LLMError`.
- `complete_with_ladder` (`gateway.py:53-71`) therefore aborts instead of escalating, which is the one behaviour the ladder exists for.
- Fix: catch `ValueError` around `json.loads` and treat it as a validator failure in the ladder. For the non-ladder path, raise `ProviderError("invalid JSON")`. Also check `finish_reason == "length"`.

### P1-4. `DRY_RUN` is inert
- Grep shows `dry_run` is read only in `config.py:26` and printed in `cli.py:29`. Nothing in the gateway or provider consults it.
- The ticket decision "dry-run default" is therefore not enforced. The only current guard is the `--yes` flag on `llm-smoke`.
- Fix: in `Gateway._call`, when `settings.dry_run` is true, refuse real provider calls (raise `DryRunActive`) unless a flag explicitly allows them. Add a test.

### P1-5. Fabricated price verification date
- `src/jobai/llm/pricing.py:9`: `VERIFIED_AT = date(2026, 11, 3)` with the comment "developers.openai.com/api/docs/pricing". No check against that source was run (no network in WP0, and the ticket says to verify with the owner's key). The date is today.
- Consequence: the 30-day STALE warning (`pricing.py:37-39`) cannot fire for 30 days, and the "verified" claim is false.
- Fix: set `verified_at` to the date the prices were actually checked, or mark the table `UNVERIFIED` and make `get_price` fail closed until it is verified. The ticket's own activity log lists this as not verified.

### P1-6. Migration failure leaves an open transaction (and the runner is not safe against concurrent runs)
- `src/jobai/db.py:36-38`: `executescript("BEGIN; ...; COMMIT;")`. If the SQL fails, the `BEGIN` is never rolled back. The connection stays inside an open write transaction, which blocks every other writer until it is closed. `SpendGuard._conn` (`caps.py:25-28`) calls `migrate` on every `reserve`, so a failure there can block the cap check.
- Concurrency: two processes can both see `0001_init` as unapplied and both run it. The second one fails with a duplicate-table or primary-key error. The version check is not repeated inside the transaction.
- Fix: wrap in `try/except: conn.execute("ROLLBACK"); raise`. Take `BEGIN IMMEDIATE`, re-read `schema_migrations` inside it, then apply. Do not call `migrate` from `reserve`; call it once at startup. Add a test with a deliberately broken migration that asserts the connection is not in a transaction afterwards.

### P1-7. Migrations are silently skipped when packaged
- `src/jobai/db.py:6`: `DEFAULT_MIGRATIONS = parents[2] / "migrations"`. `pyproject.toml:20-21` ships only `src/jobai` in the wheel, so `migrations/` is not in it. An installed copy would find no files, `migrate()` would return `[]` ("up to date"), and the app would fail later with "no such table".
- Fix: make `migrate()` raise if the directory is missing or contains no `*.sql`. Ship the migrations inside the package (for example `src/jobai/migrations/`) and include them in the wheel.

---

## P2 (should fix; can be deferred within WP0 or tracked)

### P2-1. Day and month windows depend on the caller's timezone
- `caps.py:42-48` and `ledger.py:42-47` format `now` directly. The default is `datetime.now(UTC)`, so the default is right, but a tz-aware non-UTC or naive `now` (accepted by `reserve(now=...)`) gives wrong day or month boundaries.
- Fix: `now = now.astimezone(UTC)` in `reserve` and reject naive datetimes.

### P2-2. Day filter cannot use the index and runs under the write lock
- `ledger.py:34-39`: `WHERE substr(ts,1,?) = ?` is a function on the column, so `idx_llm_calls_ts` is not used. It scans `llm_calls` inside `BEGIN IMMEDIATE`.
- Fix: `WHERE ts >= ? AND ts < ?` with the start of the day or month and the start of the next period.

### P2-3. Cap rounding is half-even, which can round a cap up
- `config.py:12-13`: `to_integral_value()` uses ROUND_HALF_EVEN. A cap of `1.0000015` becomes `1.000002`, which allows more than was configured.
- Fix: `to_integral_value(rounding=ROUND_FLOOR)`. Also reject caps <= 0 or negative with a pydantic `gt=0` validator. Caps are currently not validated at all.

### P2-4. Phantom reservations after a crash
- `caps.py:83-101`: a process that dies between `reserve` and `settle`/`release` leaves the worst-case row in `llm_calls` forever. That is the safe direction for spend, but it blocks legitimate calls for the rest of the day or month.
- Fix: add `status` (`reserved|settled`) and a reaper that releases `reserved` rows older than the timeout plus margin (for example 5 min).

### P2-5. Settle failure loses the actual cost and the output
- `gateway.py:100-106`: if `settle` raises (busy timeout after 30 s), the provider output is discarded and the reservation stays at worst case. That is safe for the cap but loses the output text and the real cost record.
- Fix: retry `settle` a few times, and log the output id and actual usage at WARNING without content.

### P2-6. Redactor repr exposes PII and mapping
- `redact.py:10-16`: the dataclass auto-repr prints `name`, `email`, `phone`, `address`, and `mapping` (which holds the original values). Any future `log.debug("%r", redactor)` or traceback leaks them.
- Fix: `field(repr=False)` on all of them, and a custom `__repr__` that shows only counts.

### P2-7. Redaction restore is fragile
- `redact.py:42-45`: restore is a plain `str.replace` in insertion order, and it runs before `json.loads` (`gateway.py:107` then `112`). A name containing `"` or `\` breaks the JSON. A model that paraphrases a placeholder (`[NAME]`, lowercase) is not restored.
- A literal name like "Name" or "Email" matches inside the placeholder text itself (`[[NAME]]` contains `NAME`), so placeholders are not protected from re-matching.
- Partial names leak: `Jane Doe` does not redact `Jane D.`. Literal-only matching is a known limit; document it.
- Fix: restore inside parsed JSON string values, or JSON-escape values before insertion. Use placeholder tokens that cannot collide (for example `⁣NAME⁣`), and add a test for each case.

### P2-8. Strict structured-output schema is not validated
- `openai_provider.py:49-53` sends `"strict": True` without checking the schema. OpenAI strict mode requires `additionalProperties: false` and all properties required. A bad schema returns a 400 that becomes a generic `ProviderError` (`openai_provider.py:65-66`), and the test schema `{"type": "object"}` (`test_gateway.py:125`) would be rejected by the real API.
- Fix: validate the schema in WP0 (`additionalProperties`, `required`) and add a provider-shape test.

### P2-9. Provider retry and backoff details
- `openai_provider.py:62`: `min(2**attempt, 20)` has no jitter and ignores `Retry-After` on `RateLimitError`.
- Worst-case blocking time is about 4 x 60 s plus about 14 s of sleep, synchronously.
- `openai_provider.py:72` returns `""` for a null `content`. Same as P1-3.
- Fix: add jitter, honour `Retry-After`, and set an overall deadline.

### P2-10. Exception traceback can carry server-echoed prompt text
- `openai_provider.py:66` chains the original `openai` exception with `from exc`. The CLI does not catch it (`cli.py:44-51`), so a traceback printed to stderr can include the API error body, which may echo input.
- Fix: in the CLI, catch `LLMError` and print the class name only.

### P2-11. Schema constraints missing in migration
- `0001_init.sql:43`: `applications.status` has no CHECK (it is a status enum in the spec). `jobs.status` (line 23) has none either.
- `0001_init.sql:59`: `llm_calls.cost_micro_usd` has no `CHECK (cost_micro_usd >= 0)`. `in_tokens`, `cached_tokens`, `out_tokens` have no `>= 0` checks either.
- Fix: add the CHECK constraints in a new migration `0002_*`. Do not edit `0001` after it has been applied anywhere.

### P2-12. Unknown model raises KeyError, not an LLMError
- `pricing.py:35`: the KeyError is correct behaviour (fail closed, before any reservation, since `gateway.py:86` runs before `reserve`), but callers catching `LLMError` will miss it.
- Fix: raise `UnknownModel(LLMError)`.

### P2-13. Config `Settings` lacks validation for list and model names
- `config.py:28`: `tailor_models` is a `list[str]` with no non-empty or allowed-model check. `TAILOR_MODELS=gpt-6-luna` (no JSON) fails at load with an unclear error.
- Fix: validator for non-empty ladder and known models (`pricing.PRICES`).

### P2-14. Migration runner calls `migrate` on every reserve
- `caps.py:25-28`: every `reserve` opens a connection and runs the migration check. This adds latency and creates the race in P1-6.
- Fix: run migrate once in the entry point.

---

## Checked and OK

- Reservation is before the call (`gateway.py:87` before `:95`). The reserve transaction is `BEGIN IMMEDIATE` with ROLLBACK on any exception (`caps.py:45-74`). `test_cap_concurrency_safe` runs 8 real threads and checks 3 allowed and 5 denied. Good.
- Failed provider call releases the reservation (`gateway.py:94-98`, `test_failed_call_releases_reservation`).
- Kill switch is checked inside `reserve` before any spend and before the provider call (`caps.py:40`). `test_kill_switch_blocks` covers it. The gateway raises before the provider is touched.
- Money is integer micro-USD. `cost_micro` rounds up (`pricing.py:50`), which is the safe direction. `format_usd` is integer-only. No float in the money path. `test_cost_no_float_drift` covers it.
- Unknown model fails closed before reservation (`gateway.py:86` calls `pricing.worst_case_micro` first).
- Logging: `gateway.py:108-111` logs purpose, model, token counts and cost only. No prompt or completion content at any level. `cli.py` prints counts only. `test_no_prompt_or_completion_at_info` covers it. `SecretStr` masks the key in `repr` and `str` (`config.py:21`, `test_secret_not_in_repr`).
- Provider timeout is 60 s with SDK `max_retries=0` (`openai_provider.py:33`). Retry is limited to connection, timeout, rate-limit and 5xx (`openai_provider.py:14-19`). Other `OpenAIError`s are not retried (`:65-66`).
- Connections set `foreign_keys=ON`, `journal_mode=WAL` and `busy_timeout` per connection (`db.py:9-17`). Tested in `test_db.py:14-15` and `test_foreign_keys_enforced`.
- Schema uniqueness: `jobs.canonical_key UNIQUE`, `UNIQUE(source, external_id)`, `applications.job_id UNIQUE`, `companies.canonical_name UNIQUE`. Route CHECK present.
- `llm_calls` day and month totals are UTC for the default path (`caps.py:42`, `ledger.py:42-47`).

---

## Missing tests (priority order)

1. Provider: no tests at all for `openai_provider.py`. Need: retry only on the four retryable errors; non-retryable maps to `ProviderError`; backoff sequence with an injected `sleep`; timeout is 60 s; no key in exception text. Use a fake `openai` client, no network.
2. Retry x reservation (P1-1): assert the ledger covers all attempts.
3. Settle and release failure paths (P2-5): a `settle` that raises must not lose the reservation silently.
4. Migration failure (P1-6): a broken SQL file leaves the connection out of a transaction; a concurrent `migrate` does not corrupt or double-apply.
5. Packaged migrations (P1-7): `migrate()` raises when the directory is empty or missing.
6. DRY_RUN (P1-4): default blocks real calls; explicit allow works.
7. `test_day_boundary_uses_utc_day` (`test_gateway.py:61-65`) has NO assertion. It only proves that two reserves do not raise. Assert that yesterday's 900_000 does not count toward today, and that a non-UTC aware `now` is converted (P2-1).
8. Unknown model through `Gateway.complete` produces no `llm_calls` row and no provider call.
9. Schema tokens counted in the reservation (P1-2).
10. JSON decode failure escalates in the ladder (P1-3); refusal (`content=None`) and `finish_reason=length`.
11. Redaction: a name that is a substring of an email or address; repeated name restore; a placeholder that the model rewrites; a name with `"` in it (JSON); `repr(Redactor)` contains no PII (P2-6, P2-7).
12. Pricing: `get_price` on an unknown model raises the intended error type; staleness with a real old `verified_at` (not just a `today` override).
13. Config: env-based `KILL_SWITCH=true` and `DRY_RUN=false` parse correctly; `OPENAI_API_KEY` from env is `SecretStr`; caps <= 0 rejected (P2-3).
14. CLI: `llm-smoke` refuses without key and without `--yes` (exit 2); `spend` output format; `migrate` twice.
15. Caps: a reservation with `worst_case_micro=0` and a negative value (should be rejected).

## Notes

- `test_redaction_round_trip_through_gateway` (`test_redact.py` / `test_gateway.py:129-148`) checks round trip with a non-JSON response. It does not cover the JSON path where P2-7 applies.
- `tests/test_pricing_config.py:49-52`: the `repr` test covers `Settings` only, not `Redactor` (P2-6).
- Ruff, mypy and pytest results are cited in the ticket activity log. They were not re-run in this review (read-only).
