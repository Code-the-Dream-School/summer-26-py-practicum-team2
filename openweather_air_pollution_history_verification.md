# OpenWeather Air Pollution History — Test & Manual Verification Notes

**Endpoint:** `GET http://api.openweathermap.org/data/2.5/air_pollution/history`
**Required params:** `lat`, `lon`, `start` (Unix UTC), `end` (Unix UTC), `appid`

---

## 1. Valid location input

| Case | Input | Expected |
|---|---|---|
| Known city coords | `lat=51.5074, lon=-0.1278` (London), valid `start`/`end` range post-2020-11-27 | HTTP 200, `list` array populated with hourly records containing `main.aqi` and `components` |
| Boundary coords | `lat=90, lon=180` / `lat=-90, lon=-180` | HTTP 200, `list` may be empty (no station data) but response is well-formed |
| Narrow time window (1 hour) | `start` and `end` 3600s apart | HTTP 200, `list` has 0–1 entries |

**Manual check:** Confirm `dt` values in each record fall within `[start, end]` and are in ascending order.

## 2. Invalid location input

| Case | Input | Expected |
|---|---|---|
| Out-of-range latitude | `lat=200` | HTTP 400, `{"cod":400,"message":"wrong latitude"}` |
| Out-of-range longitude | `lon=-500` | HTTP 400, similar `message` for longitude |
| Non-numeric coords | `lat=abc, lon=xyz` | HTTP 400 |
| Missing `lat` or `lon` | omit one | HTTP 400, `message` naming the missing param |

**Manual check:** Confirm the pipeline does not silently swallow a 400 and instead surfaces it (log, raised exception, or skipped-with-reason record) rather than writing a null/empty row to the raw table.

## 3. Missing configuration

| Case | Condition | Expected |
|---|---|---|
| Missing/empty `appid` | API key env var unset or blank string | HTTP 401, `{"cod":401,"message":"Invalid API key..."}` — verify the call is never sent with an empty key silently accepted |
| Invalid `appid` | Malformed or revoked key | HTTP 401 |
| Missing DB connection config | Postgres host/user/pass unset | Should fail fast at startup (config validation), not partway through a batch after successful API calls |
| Missing city config row | City requested has no geocode cache entry and geocoding step is skipped/misconfigured | Pipeline should not call the history endpoint with `lat=None, lon=None`; verify this is caught before the HTTP call, not after |

**Manual check:** Run the extractor with the API key env var deliberately unset and confirm it fails with a clear, actionable error rather than a raw `KeyError` or a 401 buried in logs.

## 4. Empty or malformed responses

| Case | Condition | Expected |
|---|---|---|
| Empty `list` | Valid request, no station data for that time/place | Treated as a valid zero-row result, not an error; downstream transform should handle 0 rows gracefully |
| Truncated/invalid JSON | Simulate via mocked response body (e.g. cut off mid-object) | JSON decode failure should be caught explicitly, not crash the whole batch run |
| Missing expected fields | Record present but `components` or `main.aqi` absent | Transform step should either skip the record with a logged reason or fill a defined null/default, not throw an unhandled `KeyError` |
| Unexpected schema (OpenWeather changes response shape) | Extra/renamed fields | Pipeline should not fail hard on unknown extra fields; missing expected fields should be flagged |
| Non-JSON response body (e.g. HTML error page from a proxy/gateway) | Simulate via mock | Should be caught by content-type check or try/except around `.json()`, not passed downstream as raw text |

**Manual check:** Feed a mocked malformed payload through the raw-to-gold transform step in isolation and confirm it fails loudly (logged, countable) rather than producing a silently incomplete gold row.

## 5. Predictable API errors

| HTTP Code | Meaning | Expected pipeline behavior |
|---|---|---|
| 400 | Bad request (invalid params) | Log and skip this city/window; do not retry (retrying won't fix bad input) |
| 401 | Invalid/missing API key | Fail the batch run immediately — this affects every subsequent call, so don't burn through remaining cities first |
| 404 | Not found (rare for this endpoint) | Log and skip |
| 429 | Rate limit exceeded | Backoff and retry (respect `Retry-After` header if present); confirm the pipeline doesn't hammer the API in a tight loop |
| 5xx | OpenWeather server error | Retry with backoff a bounded number of times, then fail that unit of work and continue with the next city rather than aborting the whole batch |
| Network timeout | Connection/read timeout | Treated distinctly from a 5xx — should also retry with backoff, bounded attempts |

---