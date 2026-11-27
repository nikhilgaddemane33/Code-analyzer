# CodeSentinel AI — Webhook Specification

## Events

| Event | Trigger |
|---|---|
| `review.started` | Review job accepted and queued |
| `review.completed` | All findings ready |
| `review.failed` | Pipeline error (timeout, parse failure, Gemini error) |
| `finding.critical` | A finding with severity=critical was detected |

---

## Payload Envelope

```json
{
  "event": "review.completed",
  "timestamp": "2026-11-26T15:30:00Z",
  "review_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "data": {
    "score": 72,
    "language": "python",
    "total_findings": 8,
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 2
  }
}
```

---

## Security — Signature Verification

Every delivery includes:
```
X-Sentinel-Signature: sha256=<hex_digest>
X-Sentinel-Timestamp: 1732633800
```

Verification (Python):
```python
import hmac, hashlib, time

def verify_signature(payload_bytes: bytes, signature_header: str, secret: str, timestamp: str) -> bool:
    # Reject if older than 5 minutes
    if abs(time.time() - int(timestamp)) > 300:
        return False
    
    expected = hmac.new(
        secret.encode(),
        msg=f"{timestamp}.".encode() + payload_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)
```

---

## Retry Policy

| Attempt | Delay |
|---|---|
| 1 (immediate) | 0 s |
| 2 | 30 s |
| 3 | 5 min |

After 3 failures, the delivery is marked `failed` and the webhook is flagged as unhealthy.  
Delivery logs are retained for **30 days**.

---

## Live Webhook Tester (UI)

The Webhooks page shows a **real-time SSE timeline**:

```
── 15:34:02  review.completed   ✓ 200   sig ✓   [expand ▼]
── 15:33:55  review.started     ✓ 200   sig ✓   [expand ▼]
── 15:28:11  finding.critical   ✗ 503          [expand ▼]  ← retry pending
```

A **"Send test event"** button posts a mock `review.completed` to the configured URL and shows the result live in the timeline.
