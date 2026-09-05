# Positioning for Track 03

Desk research checked 5 September 2026. Public documentation only. This is a design assessment, not a competitive performance test or knowledge of the judges' private preferences.

## Lead with recovery

The official [AI Revenue Recovery brief](https://razorpay.com/buildathon/) asks for detection, diagnosis, bounded execution and measured batch recovery, with escalation, stopping rules and an audit trail. It also asks for public source, architecture and a five-minute pitch.

The earlier submission spent too much of its first minute defending a benchmark. That made a recovery project sound like a research instrument. The revised demo leads with a batch, a recovered case and its receipt, then shows why other cases stopped.

The message is **“Recover failed subscriptions. Prove every action.”**

## Published alternatives

| Source | What is publicly described | Implication for this submission |
|---|---|---|
| [Razorpay Intelligent Revenue-Protect](https://razorpay.com/blog/upi-autopay-with-intelligent-revenue-protect/) | UPI AutoPay recovery, configurable retry strategies and customer re-engagement | Generic retry plus messaging is not enough differentiation |
| [Razorpay Agent Studio](https://razorpay.com/agent-studio/) | Subscription Recovery diagnoses failures, applies retry logic and sends targeted nudges | Do not claim Razorpay lacks recovery or AI |
| [Stripe Revenue Recovery](https://docs.stripe.com/billing/revenue-recovery) | Smart Retries, configurable schedules and failed-payment communications | Competing on retry automation alone overlooks a mature incumbent category |
| [Chargebee Dunning](https://www.chargebee.com/docs/payments/2.0/dunning/dunning-v2) | Smart dunning, logged retry attempts and controls that pause attempts and emails | Recovery scheduling and customer-aware stopping are established product capabilities |
| [Cashfree Subscriptions](https://www.cashfree.com/docs/payments/subscription/faq) | UPI AutoPay subscriptions and retry APIs | India-specific recurring payments are not an uncontested category |
| [HappyGarg8o's Track 3 repository](https://github.com/HappyGarg8o/ai-revenue-recovery) | A documented tiered recovery workflow, stopping rules checked again before intervention, and auditable dry-run outcomes | Other entrants also care about safe execution; do not portray them all as unconstrained chatbots |
| [Revenue Resilience AI](https://github.com/srikrishna0603/razorpay-buildathon) | Typed diagnosis, deterministic payment authority, SQLite WAL reservations, concurrency and stale-reservation demonstrations | AI without payment authority is shared architecture, not our unique invention; persistent concurrency handling is a useful strength to assess against our simulator |

The entrant comparison is based on their READMEs and Revenue Resilience AI's decision record, not independently executed assessments. Their claimed recovery amounts are not comparable with our differently generated dataset. No superiority ranking is justified.

## Decision on the proposed last-day pivot

Keep **MandateGuard: Recover failed subscriptions. Prove every action.** The suggested all-purpose Revenue Recovery Intelligence Agent adds bank-pattern discovery, alternate routing and card expiry recovery that this project does not implement. Those claims would widen the demonstration beyond its evidence. The official brief explicitly lists mandate retry sequencing, so the focused scope fits Track 03.

The supplied review's numerical winning scores, claims of a less-crowded track and predicted superiority are not established by the cited sources. We cannot know the full submission pool or the judges' decision. Our strongest inspectable contribution is the connection between bounded recovery, comparable batch economics and verifiable evidence. Our material limitation is that batch recovery remains simulated, and the captured provider proof is a separate Test Mode example.

## What is distinctive here

- Every policy runs on the same frozen common outcome ledger.
- The evaluation exposes legitimate recovery forgone alongside prohibited value executed.
- An independent checker and mutation tests challenge the safety implementation.
- The AI interface is deliberately bounded, including hostile-interpreter tests.
- The demo connects batch outcome, case-level calls, postconditions and downloadable audit evidence.
- A separate captured Test Mode fallback is bound to independently verified payment capture; the already-paid example records no new fallback write.

These are inspectable project properties. They are not claims that competitors or Razorpay lack equivalent internal controls.

## What prior awards actually suggest

Razorpay reports that its DrishtiPay product won at RBI's HaRBInger 2023. It addressed payment accessibility for visually impaired users. The announcement describes judging dimensions including demonstration, user experience, security and implementation practicality. This was a **different competition**, not a prior edition of the current AI Buildathon. [Razorpay announcement](https://razorpay.com/newsroom/razorpay-pos-awarded-first-prize-at-rbis-global-hackathon-harbinger-for-drishtipay-a-solution-which-facilitates-ease-to-use-digital-payments-for-visually-impaired/)

Our inference: a specific user problem, visible working flow and graceful failure are a better presentation strategy than a long feature list. This is an inference, not a published scoring rubric for Track 3. We found no verified prior-winner list for this same student program and do not invent one.

## What would weaken this position

- A judge cannot see recovery happen across the batch without reading the research.
- The UI claims live execution while showing canned labels or fabricated hashes.
- Recorded Test Mode payment capture is misrepresented as merchant revenue.
- The AI contribution is asserted rather than measured against deterministic diagnosis.
- Stronger controls are presented without showing their lost recovery or cost assumptions.
- The provider example is treated as proof of production AutoPay execution.
- An equivalent evaluation and evidence workflow is already available to the intended user with lower adoption cost.

## Reference-policy discipline

`RZP` borrows a fixed retry schedule from Razorpay's published **card** subscription documentation. Applying that schedule to this synthetic UPI AutoPay ledger is an explicit assumption. It is not a reproduction of Intelligent UPI Retry or evidence about Razorpay's current production recovery.

Use the [generated frontier](../outputs/frontier.png) and [complete price sweep](../outputs/sensitivity.png) together. Never headline “we beat Razorpay.” The useful question is what the tested policies trade off under the stated synthetic assumptions.

## Recommended demo emphasis

Recovery batch → recovered receipt → revoked mandate → uncertain timeout → captured Test Mode proof → policy trade-offs.

Keep this research as panel backup. It should not consume the opening minute.
