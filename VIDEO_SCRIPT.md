# MandateGuard — five-minute submission video

Use this script. The shorter script formerly embedded in the submission pack is retired.

**Remember:** Recover failed subscriptions. Prove every action.

Do not open with a recovery number. Open with the merchant's problem, then immediately demonstrate the batch. Keep the cursor deliberate and the screen at 100% zoom. Use the local Python-backed dashboard at `http://127.0.0.1:8765` so “Run” executes the engine.

## 0:00–0:25 — A concrete problem

**Screen:** Recovery overview.

“A subscription payment fails. Retrying might save it. But the customer might have cancelled, or the bank might still be processing it. MandateGuard finds the right next step for scheduled UPI AutoPay failures, executes within permission, and gives every decision a receipt.”

“This dashboard uses a synthetic batch and local provider simulator. These are not merchant revenue figures.”

## 0:25–1:15 — Show recovery across a batch

**Action:** Click **Run recovery batch**. Point to recovery, human review, and calls on stopped cases.

“This executes one hundred failures. The recovery total comes from successful provider outcomes, not a predicted success rate. The other cases remain visible: stopped, awaiting an outcome, or escalated to a human.”

**Action:** Select **Recovered**, open a receipt.

“Here is one recovery: the diagnosis, mandate state, authorized action, provider call and postcondition. The idempotency key is in the downloaded receipt.”

**Action:** Click **Verify audit chain**.

“The browser recomputes the hashes. Editing a decision breaks verification. This is tamper-evident evidence, not immutable storage.”

## 1:15–2:10 — Prove the stopping rules

**Screen:** Failure lab.

**Action:** Choose **Customer cancelled**, click **Run scenario**.

“The bank error still looks retryable. The mandate is revoked, so the policy stops before the provider. Zero calls.”

**Action:** Choose **AI is uncertain**, run.

“B3 can interpret ambiguous signals, but low confidence means human review. The model gets no payment tools and cannot override consent or limits. This repeatable demo uses deterministic interpretation; the captured optional real-model run is available below.”

**Action:** Choose **Provider timed out**, run.

“This one is different: a call happened, but the outcome is unknown. We do not call that a failed payment or retry blindly. Further automated action waits for human review.”

## 2:10–3:05 — Show the Razorpay integration

**Screen:** Razorpay proof.

“Here is a separate captured Razorpay Test Mode run. RecoveryTruth read the original order and payments, checked again immediately before the write, and created a Standard Payment Link fallback. That fallback is customer-initiated; it is not an AutoPay retry.”

“A created link is not recovered money. The saved proof independently verifies the captured payment and binds it to the original case, decision, link, amount and currency.”

**Action:** Point to the already-paid card.

“In the second case, the original order was already paid. Payment Links stayed zero to zero: no new collection object was created. These are saved Test Mode artifacts, not a fresh live call from this viewer.”

## 3:05–4:05 — Explain the policy trade-off

**Screen:** Policy comparison.

“The product also compares nine policies on exactly the same frozen outcomes. You can recover more by ignoring controls, but that can send prohibited actions. Stronger controls also forgo some legitimate recovery. Both costs are measured.”

“RZP is only a fixed temporal reference derived from Razorpay's published card schedule. It is not Razorpay's current Intelligent UPI Retry Engine, and I have not benchmarked Razorpay's production logic.”

**Action:** Scroll to the full price sweep; switch pricing model.

“The preferred policy changes with the assumed price of a violation or prohibited value. There is no single universal winner. The diagnostic relaxed policies help us understand this frontier; they are not safe production defaults.”

## 4:05–4:40 — Architecture and practical fit

**Screen:** Return to recovery overview; point to the four-step workflow.

“The boundaries are simple: authenticate, diagnose, authorize, execute, verify. AI interprets; deterministic policy authorizes. The production gap is also explicit: durable state, merchant access control, approved provider execution and validation on real permissioned data.”

“Razorpay already offers recovery. My proposed integration is an evidence-backed configuration workflow: inspect what a policy recovers and refuses before rolling it out.”

## 4:40–5:00 — Close

“MandateGuard demonstrates recovery across a batch, a real Test Mode integration, and failures handled without hiding the cost. Recover failed subscriptions. Prove every action.”

Leave the source and demo links visible. End before five minutes.

## Recording checklist

- Rehearse once. Spend time on actions and evidence, not the arm names.
- Use **Run** only when the header says **Python engine connected**. Static Pages is explicitly a recorded evidence replay.
- Never call simulation production revenue, a Payment Link an AutoPay retry, or the hash chain tamper-proof.
- Do not claim a model accuracy improvement from the single captured model artifact.
- Upload the video with accessible viewing permissions and test it signed out. Use this file as narration, not as a substitute for the video.
