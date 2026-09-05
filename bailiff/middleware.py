"""Process-local webhook gate for a demo host; never executes a provider action.

Use the authenticated, bounded decision in request.state.mandateguard. A real
provider integration still needs durable delivery state and a fresh write fence.
"""
import json
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .domain import Decision
from .guardrails import AuditChain, EvaluationContext, GuardrailEngine
from .policies import _authority, default_policy, deterministic_diagnosis, proposed_action
from .razorpay_adapter import RazorpayPayloadError, normalize_razorpay_autopay_payload
from .replay import CommonOutcomeLedger, ReplayProvider
from .state import CaseStore
from .webhook import WebhookGate


class MandateGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, webhook_secret: str, webhook_path: str = "/webhook/razorpay",
                 policy: str = "B2", fail_closed: bool = True):
        super().__init__(app)
        if policy != "B2" or not fail_closed:
            raise ValueError("middleware requires the fully guarded B2 policy and fail_closed=True")
        self.webhook_path = webhook_path
        self.policy = default_policy(policy)
        self.gate = WebhookGate(secrets=(webhook_secret,))

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path != self.webhook_path or request.method != "POST":
            return await call_next(request)
        raw_body = await request.body()
        verdict = self.gate.verify(raw_body=raw_body, headers=dict(request.headers))
        if not verdict.accepted:
            return JSONResponse(status_code=401, content={"error": "WEBHOOK_AUTHENTICATION_FAILED",
                "reason": verdict.reason_code, "provider_calls": 0})
        if not verdict.should_process or verdict.event_name != "payment.failed":
            return JSONResponse({"status": "IGNORED_NON_ACTIONABLE", "reason": verdict.reason_code,
                                 "provider_calls": 0})
        try:
            event = normalize_razorpay_autopay_payload(json.loads(raw_body))
        except (ValueError, TypeError, RazorpayPayloadError) as exc:
            return JSONResponse(status_code=422, content={"error": "PAYLOAD_NORMALIZATION_FAILED",
                                                          "detail": str(exc), "provider_calls": 0})
        cases = CaseStore()
        cases.create_or_get(event)
        audit = AuditChain()
        engine = GuardrailEngine(cases=cases, provider=ReplayProvider(CommonOutcomeLedger()), audit=audit)
        reason, confidence = deterministic_diagnosis(event)
        decision = engine.evaluate(EvaluationContext(event=event, policy=self.policy,
            proposed_action=proposed_action("B2", reason, attempt_count=event.attempt_count),
            authority=_authority(event, self.policy), diagnosed_reason=reason, confidence=confidence))
        request.state.mandateguard = {"decision": decision.decision.value,
            "final_action": decision.final_action.value if decision.final_action else None,
            "reason_codes": list(decision.reason_codes), "audit_hash": audit.events[-1]["event_hash"],
            "provider_calls": 0, "audit_verified": audit.verify()}
        if decision.decision != Decision.ALLOW:
            return JSONResponse({"status": "REFUSED_BEFORE_PROVIDER_BOUNDARY", **request.state.mandateguard})
        return await call_next(request)
