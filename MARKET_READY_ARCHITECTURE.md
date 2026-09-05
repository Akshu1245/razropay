# Production boundary and integration path

This is a hackathon prototype, not a market-ready payment service. This filename is retained for existing links; earlier statements implying installed Redis, PostgreSQL, Kubernetes or a production Razorpay integration were inaccurate.

## Implemented

- Deterministic recovery policies, bounded optional interpretation and guardrail evaluation.
- In-memory provider simulator, case state, delivery deduplication and audit chain.
- Stateless public demo API with a fixed synthetic workload.
- Static evidence replay and a Python-backed recovery dashboard.
- Separate Razorpay Test Mode client, expiring fallback authority, fresh provider reads, write fence, reconciliation lookup and captured-payment verification.
- Recorded Test Mode evidence with hash and cross-artifact binding verification.

## Required before merchant traffic

| Gap | Integration work |
|---|---|
| Process-local state | Durable event inbox, case state and idempotency records |
| Concurrent workers | Transactional claims and recovery after crashes; test cross-process races |
| Payment authority | Merchant authentication, tenant isolation, secret management and approved provider capabilities |
| Write/read race | Provider guarantees or reconciliation that handles changes between the last read and write |
| Evidence retention | External audit anchoring, retention policy and access controls |
| Retry scheduling | Durable scheduler and cancellation of pending work |
| Model validation | Permissioned real failures, held-out labels, abstention calibration, model cost and latency |
| Economic validation | Merchant cohort outcomes and operational review cost |

The Test Mode client uses process-local locks plus deterministic references. This is not distributed exactly-once execution. A pre-write reread is not an atomic transaction with Razorpay. The middleware checks a decision but does not itself execute a payment.

Use [DEPLOYMENT.md](docs/DEPLOYMENT.md) for the actual demo commands and [.env.example](.env.example) for environment variables the code really reads. No production credentials are accepted by RecoveryTruth.
