# auth.json Inspection Report

## File: /Users/fireant/.codex/auth.json

---

## 1. Full JSON Structure (Sensitive Values Redacted)

```json
{
  "auth_mode": "chatgpt",
  "OPENAI_API_KEY": null,
  "tokens": {
    "id_token": "eyJhbGciOi...[REDACTED, 2108 chars]...hraq9aPy2E",
    "access_token": "eyJhbGciOi...[REDACTED, 1975 chars]...ZFvP8kTHDM",
    "refresh_token": "rt_wc3PNuE...[REDACTED, 90 chars]...7ag5GbHDnY",
    "account_id": "392780e2-41b0-4309-b1f8-0c648f9851ef"
  },
  "last_refresh": "2026-04-09T14:24:11.759944Z"
}
```

---

## 2. Top-Level and Nested Keys

### Top-Level Keys
| Key | Type | Description |
|-----|------|-------------|
| `auth_mode` | string | `"chatgpt"` — indicates ChatGPT OAuth-based auth |
| `OPENAI_API_KEY` | null | Not set; auth uses OAuth tokens instead |
| `tokens` | object | Contains all OAuth token material |
| `last_refresh` | string (ISO 8601) | Last token refresh timestamp |

### Nested Keys under `tokens`
| Key | Type | Description |
|-----|------|-------------|
| `id_token` | string (JWT) | OpenID Connect identity token |
| `access_token` | string (JWT) | OAuth2 access token for API calls |
| `refresh_token` | string (opaque) | OAuth2 refresh token |
| `account_id` | string (UUID) | OpenAI account identifier |

### Expiry/Refresh-Related Fields
- **access_token JWT `exp` claim**: `1776608650` → `2026-04-19T14:24:10 UTC`
- **access_token JWT `iat` claim**: `1775744649` → `2026-04-09T14:24:09 UTC`
- **access_token JWT `nbf` claim**: `1775744649`
- **id_token JWT `exp` claim**: `1775748849` → `2026-04-09T15:24:09 UTC` (already expired)
- **last_refresh**: `2026-04-09T14:24:11.759944Z`
- **No explicit `expires_in` or `token_expiry` field** in the JSON; expiry is embedded in JWT payloads.

---

## 3. Token Format Identification

| Token | Format | Details |
|-------|--------|---------|
| `access_token` | **JWT** (3 base64url segments) | Header: `{"alg":"RS256","kid":"19344e65-...","typ":"JWT"}` |
| `id_token` | **JWT** (3 base64url segments) | Header: `{"alg":"RS256","kid":"b1dd3f8f-...","typ":"JWT"}` |
| `refresh_token` | **Opaque** | Prefix `rt_` + random string, NOT JWT-decodable |

---

## 4. Access Token Expiry Calculation

| Metric | Value |
|--------|-------|
| Token issued at (iat) | 2026-04-09 14:24:09 UTC |
| Token expires at (exp) | 2026-04-19 14:24:10 UTC |
| Total token lifetime | **10 days** |
| Current time (UTC) | 2026-04-14 ~16:04 UTC |
| **Remaining time** | **≈ 4.93 days** |
| Last refresh age | ~5.1 days ago (121.7 hours) |

### ⚠️ THRESHOLD CHECK: 4.93 days ≤ 5 days → **ADDITIONAL ACTION WARRANTED**

The access_token has approximately **4 days and 22 hours** of remaining validity, which is **at or below the 5-day threshold** specified in the original request.

---

## 5. Additional Observations

1. **id_token is already expired** — it expired on 2026-04-09 at 15:24:09 UTC (~5 days ago). This is normal; id_tokens typically have very short lifetimes (~1 hour) and are used only for initial authentication.

2. **refresh_token is opaque** — it starts with `rt_` and cannot be decoded. It should be used to obtain new access/id tokens via the OAuth refresh flow.

3. **Account type**: ChatGPT Team plan (`chatgpt_plan_type: "team"`).

4. **Subscription active until**: 2027-02-28 (`chatgpt_subscription_active_until`).

5. **No explicit `expires_in` or `token_expiry` top-level field** exists in the JSON; all expiry information is encoded within the JWT `exp` claims.
