# Panel Q&A — the questions most likely to be asked, and the answer that survives follow-up

This document exists for one purpose: so the first time you say these answers
out loud is not in front of the panel. Read each question, say the answer to
yourself before you read the notes, then check it against what's here. If your
version is shorter and still true, use yours — a memorized paragraph reads as
memorized, and a panel notices instantly.

---

### "This is Track 03. Where's the agent that executes recovery? Your README used to say you're not a recovery engine."

Nine arms are nine competing recovery agents. Seven of them execute real
retries in the benchmark when they decide to. The thing that makes this
different from "just build a retry agent" is that a retry agent which always
retries wins on recovered money and loses on everything else — mandate state,
consent, prohibited debits. This project is what happens when you build the
agent *and* insist on proving, before it ships, which version of it should be
trusted with a merchant's money. That proof is not a side document, it's
`outputs/frontier.png` and the hash-chained receipt on every single decision.

Do not open with the disclaimer. Open with: "we built nine recovery agents
and ran a tournament — here's who won and why the obvious answer lost."

---

### "Where's the actual AI? Everything I'm seeing looks like a rules engine."

Correct, and deliberate. Eight of the nine arms are rules because the failure
modes they handle — a cancelled mandate, an exhausted retry budget, consent
withdrawn — don't need a model to classify; a model there would just be
latency and cost with no accuracy gain, and this project doesn't fake AI usage
to check a box. The one arm that needs a model, `B3`, calls one for real: not
a mock, not a canned string — `outputs/real_interpreter_evidence.json` is an
actual captured response from `openai/gpt-oss-20b`, ambiguous failure in,
taxonomy reason and confidence out. The interesting design decision isn't
"we used an LLM," it's "we used an LLM and then refused to let its opinion
become authority" — the model's confidence still has to clear a threshold
this codebase enforces, not the model, before its answer changes anything.
If confidence is low, it abstains to human review with zero provider calls,
regardless of what the model said.

Say the restraint out loud before they ask why AI usage looks thin. If you
wait for the question, it sounds like an excuse instead of the thesis.

---

### "You're beating a strawman. You implemented the *card* schedule, not Razorpay's current UPI retry engine."

Correct — and the repository says so before the benchmark result. `RZP` is a
**fixed temporal reference arm** derived from Razorpay's documented card retry
schedule. It is not a reproduction or benchmark of Razorpay's current
Intelligent UPI Retry Engine, and MandateGuard has not been evaluated against
Razorpay's production decision logic. The result is narrower: on the same
synthetic scheduled AutoPay ledger, the tested reason-aware policies recover
more while moving less prohibited value than that fixed temporal reference.

If pushed further: "what would change your mind?" — an independently
reproducible UPI retry policy evaluated on the same frozen ledger and metrics
that matches or outperforms the reason-aware arms. The harness is designed to
accept such a policy as another benchmark arm.

---

### "Is this real, or is it just a synthetic simulation with big numbers on a chart?"

It is a synthetic simulation, stated as such in the first mention of it in
the README and repeated in `FINDINGS.md`'s limitations section. No Razorpay
API is called, no production money moves. What's real: the webhook
authentication logic (`bailiff/webhook.py`) implements Razorpay's actual
published HMAC contract and is attacked 39 ways in tests; the guardrail
engine is a real state machine that really refuses actions, provably, not by
convention; and in the optional real-interpreter mode the LLM call is a real
API call with real tokens and real cost (the default benchmark does not make
it).
The rupee figures are counterfactual attribution over a frozen synthetic
ledger, and the project says so before it says anything else about them —
don't let a panelist "catch" you conceding this, concede it first.

---

### "Your test suite is huge and your rigor language is unusual for a hackathon project. Is any of this real, or is it AI-generated boilerplate?"

Answer with one falsifiable fact, not a defense of the volume: mutation
testing (`scripts/mutation_check.py`) reintroduces 13 known defects into the
codebase one at a time and confirms the test suite catches every one — if you
delete the check that stops a denied retry from reaching the provider, a test
fails. That's not boilerplate, it's a claim you can break on demand: "pick any
one of the 13 mutations, I'll show you the exact test that catches it." Offer
to demo it live if there's time. Do not lead with the number 198; lead with
"I can show you the test suite catching a real bug I put back in on purpose."

---

### "What broke during development, and how did you fix it?"

Not a required field on this application, but assume it'll come up
conversationally. Have one real answer ready, not a rehearsed list — the
authentic one is the webhook: the project's whole thesis is "authority
control before the provider boundary," and for a while the boundary that
authenticates the *input* didn't exist at all — anyone who could POST to the
endpoint could manufacture a failure event and drive the whole system. That's
a real gap you found and closed (`bailiff/webhook.py`, 37 attack tests). It's
a good answer because it's specific, it's embarrassing in exactly the way a
true story is, and it's fixed with evidence, not assertion.

---

### "Is your GitHub repo actually public, and does it have real commit history, or did you paste in one giant commit right before the deadline?"

Answer honestly with whatever your actual history shows. If it's a small
number of large commits because most of the work happened in a compressed
window, say that plainly rather than let it look evasive — judges are
evaluating build quality and reasoning, not commit cadence for its own sake.

---

### "Did any of this exist before the buildathon started?"

Answer this one before anyone asks it, in your own head, right now, with the
true answer. A vague or hesitant answer under direct questioning costs more
than an honest "I had X before and built Y and Z during the window" ever
would.

---

## The one thing to get right regardless of which question lands

Every hard question above has the same shape: concede the real limitation in
one sentence, then pivot immediately to the specific, checkable thing that
survives the concession. Never argue the limitation doesn't exist — every one
of these limitations is already written down in this project's own docs, on
purpose, so that conceding it live matches what's on the page instead of
contradicting it.

---

### "You added an operations console. Can it actually do anything, or does it just look like it can?"

It cannot act, and that is enforced rather than promised.

All of the lineage, exception queue and provenance logic lives in
`bailiff/lineage.py` as pure functions over evidence the benchmark already
wrote. It computes no metric, opens no ledger, calls no provider, writes no
file, and opens no socket. `app.py` only renders what those functions return.
There is no button on any screen that approves, retries, executes, or
contacts anyone.

The tests are the part worth pointing at. `tests/test_lineage_and_exception_queue.py`
replaces every public method on the provider simulator with a trap and then
builds the entire queue — any call at all fails the suite. It hashes every
canonical output before and after a full render pass and asserts nothing
changed. It blocks `socket.connect`, `socket.create_connection` and
`socket.getaddrinfo` and renders again. And it greps both files for write and
network operations, so a later edit that adds one fails rather than shipping.

Two details a reviewer should check directly. A field the evidence does not
carry displays `not present in fixture` — the benchmark ledger genuinely has
no mandate id or wire timestamps, and the panel says so on every row instead
of inferring them. And every denied or abstained row shows
`provider_calls = 0`; if a non executing row ever reported a call, the queue
raises it as an invariant contradiction rather than rendering it quietly.

---

### "Where does Rillet fit — are you integrated with them?"

It is not an integration, and nothing in the repository talks to Rillet.

Rillet's public Aura and MCP material was used as design inspiration for
contextual data access, reviewable workflow actions, permission boundaries,
and auditability. MandateGuard does not integrate with Rillet. It applies
those ideas narrowly to scheduled AutoPay recovery policy evaluation.

Concretely: there is no Rillet dependency, credential, endpoint, or runtime
reference anywhere here, and the name does not appear in the product, the UI,
the policy arm list, the API, or the benchmark. If a panelist wants to verify
that, `grep -ri rillet` over the source, the UI, and the arm list returns
nothing outside the design-credit sentences in the documentation.
