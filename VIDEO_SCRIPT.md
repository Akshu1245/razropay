# MandateGuard submission video script

## Target length

Record a focused two to three minute walkthrough. The command line evidence is the source of truth. The optional UI may be shown after the proof sequence if it is already installed and working.

## The first thirty seconds

Do not explain code. Do not open on a number. Open on the problem, in one
breath:

> Razorpay already has intelligent payment recovery. MandateGuard solves the
> next problem: before an AI recovery system retries a payment, how do we know
> the action is permitted, safe, economically useful, and provably compliant?

Then, and only then, show the system. The single sentence to land before any
demo output appears:

> **AI interprets. Policy authorizes. Provider executes. Evidence proves.**

Say plainly, once, that the evaluation dataset is a synthetic failure ledger
and the provider is a local simulator. A judge who discovers that themselves
at 3:00 discounts everything before it; a judge told at 0:30 treats it as
rigour.

## Five minute structure

| Time | Section | What is on screen |
|---|---|---|
| 0:00–0:30 | The problem | The question above. No code |
| 0:30–1:00 | Why existing retry systems do not remove it | Configurable retry makes strategy a merchant setting; nothing tells the merchant what a setting costs in prohibited debits before it is switched on |
| 1:00–1:40 | Architecture | `outputs/architecture.png` — authenticate, interpret, decide, execute, prove |
| 1:40–3:20 | Live demo | `python3 scripts/demo60.py` end to end |
| 3:20–4:10 | Evaluation and results | `outputs/frontier.png`, then `report.md` / `FINDINGS.md`, then `sensitivity.png` |
| 4:10–4:40 | The real AI interpreter | Step 8 of the demo: a live model consulted, an ambiguous failure, a real confidence score, and `provider_calls = 0` |
| 4:40–5:00 | Value to Razorpay | The evaluation layer in front of a recovery engine, not a competitor to it |

## Opening statement

Answer the competitive question before the judge has to ask it. They know what
their own product does, and a submission that talks around it reads as either
uninformed or evasive.

Say:

> Before anything else: this runtime does not trust its own input. A Razorpay webhook is authenticated with HMAC over the raw body before a single policy reads it, because an unauthenticated event is an attacker writing your failures. Everything after that point is about proving an action was allowed; this is about proving the event was real.

Then the positioning, and lead with the result rather than the claim:

> Razorpay documents a fixed retry schedule for cards: three retries, once a day, then halt. I implemented exactly that as a **fixed retry reference policy** and ran it on the same synthetic ledger as everything else. Say this next part in full, do not compress it: **we use Razorpay's documented fixed card retry schedule as a reference policy; it does not reproduce or benchmark Razorpay's current Intelligent UPI Retry Engine, and MandateGuard has not been evaluated against Razorpay's production decision logic.** On this synthetic ledger, under the tested policies, that fixed schedule is Pareto dominated in all three regimes — reading the failure reason recovers more money while moving six times less prohibited value in the terminal regime. Applying a card schedule to a scheduled AutoPay ledger is an explicit benchmark assumption, not a claim about Razorpay's UPI behaviour or production system. The result is only about the tested fixed temporal reference versus the reason-aware policies on this synthetic ledger.

> Razorpay already ships recovery for UPI AutoPay, including a configurable retry engine in beta and, since FTX'26, a Subscription Recovery agent in Agent Studio. I am not proposing a competitor to it. MandateGuard asks a separate evaluation question: before a retry strategy is deployed, what recovery-versus-prohibited-value trade-off does it produce under a declared test model? The harness measures that on a frozen synthetic ledger, while the bounded runtime proves every refusal with a receipt.

Then give the direction of the problem, because it is the opposite of what a
recovery demo normally claims:

> The documented complaint themes on recurring payments in India are unexpected and unauthorised debits, not merchants saying too little was recovered. So the metric I lead with is not money recovered. It is prohibited value that never reached the provider.

Immediately clarify the scope:

> This is a deterministic synthetic benchmark with a local provider simulator. The input is Razorpay shaped, but this demo does not call Razorpay and the numbers are not production revenue.

**Do not open with a recovery number.** The ungated arms in this benchmark
recover more than the guarded ones, that result is in the report, and leading
with a figure your own evidence beats is the fastest way to lose the room. Lead
with the denial and its receipt.

## Shot list

| Time | Action | What the judge should see |
|---|---|---|
| 0:00 to 0:20 | Run `python3 scripts/demo60.py` | A forged webhook refused at ingress, then the genuine one verified; the whole loop in one screen |
| 0:20 to 0:35 | Stay on the same output | The refused retry: `MANDATE_NOT_ACTIVE`, zero provider calls, audit chain verified |
| 0:35 to 0:50 | Stay on the same output | The permitted retry: one provider call, a call id, and a `RECOVERED` postcondition |
| 0:50 to 1:05 | Stay on the same output | Four safe failures: duplicate webhook ignored, `ABSTAIN` to human review, timeout to human review, audit tamper detected |
| 0:15 to 0:30 | Show the allowed case lines | Razorpay shaped input, one allowed retry, one provider call, recovered status, and a postcondition |
| 0:30 to 0:45 | Show the ambiguous B3 lines | `deterministic_offline`, `decision=abstain`, bounded interpreter reason, and `provider_calls=0` |
| 0:45 to 1:00 | Show the consent and timeout lines | Opted out contact denied without a provider call; unknown timeout postcondition routes to human review |
| 1:00 to 1:15 | Show the audit line | `before=True, after=False` after modifying a historical audit event |
| 1:15 to 1:45 | Run `./scripts/evaluate.sh` or show generated outputs | Nine arms, twenty fixed seeds, frozen dataset hash, economic and safety metrics |
| 1:45 to 2:10 | Open `outputs/frontier.png` first, then `outputs/report.md` and `FINDINGS.md` | The recovery against prohibited value frontier, with B0 and B2 marked as dominated; then incremental recovery, forgone value, protected value, realized harm, violations, efficiency, abstention, net value, break even, and spread |
| 2:10 to 2:35 | Open `outputs/sensitivity.png` | Which arm wins as the price of a prohibited action is swept, and the crossover where the fully guarded arms overtake reason gating alone |
| 2:35 to 3:00 | Optional: run `streamlit run app.py` | Control Room, Case Timeline (with source lineage and the ordered action provenance chain), Policy Compare, Failure Lab, and Exception Queue — all read only. Say it out loud: no control on any screen executes, approves, or contacts anyone |

## Narration for the proof

Start with the denial, not the success:

> The first result is a retry that is not permitted. The runtime stops before the provider boundary. The receipt records zero provider calls. This is the important negative proof: denial is not a logged intention after execution; it is a pre execution boundary.

Then show the permitted path:

> The next case has a transient provider signal and passes the configured authority, consent, timing, attempt, mandate, pre debit, and amount checks. It creates one idempotent provider call and records the postcondition.

Then show ambiguity:

> B3 does not give an interpreter control of payments. It interprets only an ambiguous raw signal. In this case it abstains, routes to review, and makes zero provider calls. A proposal cannot widen authority because the deterministic guardrail engine remains the only execution gate.

Close with the benchmark:

> The policy lab runs every arm on the same frozen ledger. It reports both what a policy recovered and what legitimate recovery it refused, alongside protected value, realized harm, violations, efficiency, abstention, cost, and spread. If B3 does not beat B2, the report shows that result instead of hiding it.

On the frontier chart, name the strongest single result:

> Read the front. B3, the bounded interpreter arm, dominates B2 outright in all three regimes: it moves exactly the same prohibited value, which is none, and recovers more. That is a stronger claim than saying it scored higher, because it means no weighting of these two metrics can prefer B2. The two hollow markers are the arms that are dominated: doing nothing, and the deterministic guarded arm.

If there is time for one more beat, make it the red team rather than another metric. It is the only thing on screen that a judge cannot get from any other submission:

> Here is the interpreter replaced with a hostile one. It returns the most permissive reading available at full confidence, and the payload carries prompt injection telling the system to skip the consent gate. The mandate is revoked, so the answer is still deny, still zero provider calls. Mandate state is read from the event, never from the interpretation, which is why no interpreter, compromised or not, can turn a prohibited action into a permitted one. There are forty six of these attacks and fourteen deliberately reintroduced bugs the suite has to catch.

Close by making the uncomfortable result the point rather than the caveat:

> My own benchmark says the strict policy is not always the profitable one. Reason gating alone recovers more, and under a sweep of fifteen fixture settings a fully guarded arm is the recommended policy in eighteen of forty five regime observations. If the deliverable here were a recovery policy, that would be a failed project. The deliverable is the instrument that produced the result: a harness willing to report against the person who built it. That is the only kind of measurement worth putting under a configurable retry engine.

Then close with the economics, and be direct that the controls are not free:

> The last chart is the one I would attack if I were judging this. Whether a guardrail is worth its cost depends entirely on what a prohibited action is assumed to cost, and that assumption is the weakest number in the project. So the benchmark does not pick a number and defend it. It sweeps the price and shows where the ordering flips. Under a flat charge per breach, reason gating alone is competitive, because a flat charge is indifferent to the size of the debit it prices. Once a prohibited action is charged the money it actually moved, the fully guarded arms win. That crossover is generated from the run, not typed in, and it is the honest form of the claim.

Also be explicit about the fixture, because it is the first thing a hostile judge should attack:

> Compliance exposure in the fixture is drawn independently of the failure reason. That matters. If harm were predictable from the reason code alone, the arm that reads only the reason code would capture all the safety benefit for free and no stronger control could ever be shown to be worth anything. An earlier version of this benchmark had exactly that flaw, and its own results argued against its own guardrails. The release gate now rejects that shape of fixture.

## Commands to record

```bash
./scripts/test.sh
./scripts/demo.sh
./scripts/evaluate.sh
./scripts/release_check.sh
```

Optional UI:

```bash
python3 -m pip install streamlit
streamlit run app.py
```

## Claims to avoid

Do not say that Razorpay lacks recovery. Do not call the local simulator a live payment integration. Do not describe synthetic INR as observed revenue. Do not call the project taxonomy an official NPCI taxonomy. Do not present B1, B1.5, B2.25, B2.5, or B2.75 as safe production defaults. Do not claim the guarded arms win at every price; the generated report shows they do not. State the recommendation as a threshold with its crossover. Do not claim that the optional UI is a payment console.
