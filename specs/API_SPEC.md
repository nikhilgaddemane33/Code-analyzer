# CodeSentinel AI — API Specification

Base URL: `https://api.codesentinel.ai/v1`  
Auth: `Authorization: Bearer <api_key>` **or** `X-API-Key: <api_key>`  
Format: JSON (`Content-Type: application/json`)  
Errors: RFC 7807 Problem Details

---

## Reviews

### POST `/reviews`
Submit code for review.

**Request body:**
```json
{
  "code": "string (required)",
  "language": "python|javascript|typescript|java|c|cpp|go|rust|php|ruby|sql",
  "options": {
    "categories": ["security", "quality", "performance"],
    "max_findings": 50
  }
}
```

**Response `202 Accepted`:**
```json
{
  "id": "uuid",
  "status": "pending",
  "stream_url": "/v1/reviews/{id}/stream",
  "created_at": "ISO-8601"
}
```

---

### GET `/reviews/{id}`
Fetch a completed (or in-progress) review.

**Response `200 OK`:**
```json
{
  "id": "uuid",
  "status": "completed",
  "language": "python",
  "score": 72,
  "findings": [ { ...finding schema... } ],
  "created_at": "ISO-8601",
  "completed_at": "ISO-8601"
}
```

---

### GET `/reviews/{id}/stream`
SSE stream of live review progress and findings.

**Response:** `text/event-stream`

```
event: progress
data: {"step":"parsing","index":0,"total":5}

event: finding
data: {"id":"uuid","severity":"critical","title":"SQL Injection",...}

event: progress
data: {"step":"completed","score":72}
```

---

### POST `/reviews/{id}/fix`
Apply a specific fix and return patched code.

**Request body:**
```json
{ "finding_id": "uuid", "accept": true }
```

**Response `200 OK`:**
```json
{ "patched_code": "string", "diff": "unified diff string" }
```

---

### POST `/reviews/{id}/chat`
Ask a question about the review (streaming response).

**Request body:**
```json
{
  "message": "Why is this a SQL injection vulnerability?",
  "finding_id": "uuid (optional — anchors context to a finding)"
}
```

**Response:** `text/event-stream` (chunked Gemini output)

---

## API Keys

### GET `/api-keys`
List all API keys for the authenticated user.

```json
{
  "keys": [
    {
      "id": "uuid",
      "name": "CI pipeline",
      "prefix": "sk-xK3f",
      "scopes": ["review:read", "review:write"],
      "last_used_at": "ISO-8601",
      "created_at": "ISO-8601"
    }
  ]
}
```

### POST `/api-keys`
Create a new API key. **Full key shown once in response only.**

**Request body:**
```json
{ "name": "string", "scopes": ["review:read", "review:write"] }
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "name": "string",
  "key": "sk-xK3fABCD1234...  (full, shown once)",
  "prefix": "sk-xK3f",
  "scopes": [...]
}
```

### DELETE `/api-keys/{id}`
Revoke an API key. `204 No Content`.

---

## Webhooks

### POST `/webhooks`
Register a new webhook endpoint.

**Request body:**
```json
{
  "url": "https://example.com/hook",
  "events": ["review.completed", "finding.critical"],
  "secret": "optional — if omitted, one is generated"
}
```

**Response `201 Created`:**
```json
{
  "id": "uuid",
  "url": "...",
  "events": [...],
  "secret": "whsec_... (shown once)",
  "active": true
}
```

### POST `/webhooks/{id}/test`
Trigger a test `review.completed` delivery.

**Response `200 OK`:**
```json
{ "delivery_id": "uuid", "status_code": 200, "latency_ms": 134 }
```

---

## Error format (RFC 7807)

```json
{
  "type": "https://api.codesentinel.ai/errors/rate-limit-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "You have used 500/500 reviews this month.",
  "retry_after": 1735084800
}
```

---

## Rate limits (by plan)

| Plan | Reviews/month | Requests/min |
|---|---|---|
| Free | 10 | 5 |
| Pro | 500 | 60 |
| Team | Unlimited | 300 |

Headers returned on every response:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 54
X-RateLimit-Reset: 1735084800
```
