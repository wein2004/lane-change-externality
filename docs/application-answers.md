# Smart Logistics Datathon 2026 — Open-ended Q&A

Draft answers. Limit is **200 words each**; counts are checked by
`scripts/check_answer_length.py`.

Anything in `[[double brackets]]` still needs your input.

---

## Q1. Describe one or two projects undertaken by your team members that relate to logistics, supply chain management, or data analytics.

We built *The Externality of a Lane Change*, an open-source analysis of 8.7
million vehicle-trajectory records from the US DOT's NGSIM programme: when a
vehicle changes lanes, what does it cost the traffic behind it, and does a heavy
goods vehicle cost more?

We detected 2,472 clean lane changes, measured the follower's speed loss and
recovery, and compared each against matched moments where no lane change
occurred, paired on pre-event speed, acceleration trend and headway.

We expected trucks to impose a larger cost. The data rejected it. Truck cut-ins cost the follower 1.62 km/h *less* than car cut-ins
(95% CI −3.12 to −0.02), and controlling for traffic state, vehicle class is
indistinguishable from zero (p = 0.47). What survives is congestion: every
1 km/h slower the surrounding traffic, the same manoeuvre costs 0.35 km/h more
(p < 0.001). The externality belongs to the moment, not the vehicle.

Four data defects surfaced, one reversing the headline's sign; all documented
publicly.

We are two final-year Information Management students at NCCU — a discipline
spanning systems and business — which is why this runs from raw trajectories
through to a costed service concept, not just statistics.

---

## Q2. Drawing on a project described above, how may it be packaged as a "service" and what may make the service "smart"?

The finding productises directly as a **Congestion Externality Score** for
fleet operators: an API that consumes the GPS traces operators already collect
for compliance and insurance, and returns, per driver and per route, the delay
their manoeuvres imposed on surrounding traffic.

Existing telematics scores — harsh braking, speeding, idling — all measure risk
to the driver's *own* vehicle. None price the cost paid by everyone else. That
cost is invisible to the driver, because it happens behind them.

Three things make it smart rather than merely automated.

First, it is **context-priced, not rule-based**: our regression shows the same
manoeuvre costs 0.35 km/h more per 1 km/h that surrounding traffic slows, so the
score weights each event by measured traffic state instead of a fixed penalty.

Second, it is **benchmarked against demonstrated behaviour**, not an abstract
ideal. Professional drivers in our data already impose less cost than car
drivers, so the target is an observed standard.

Third, it **closes the loop**: coaching changes behaviour, the change is
re-measured, and the model is re-estimated — so the service learns what actually
works for each fleet rather than asserting it.

---

## Q3. Based on the same project experience, explain how Artificial Intelligence (AI) and data analytics work together to further enhance the project results?

In our project the two did different jobs, and each caught the other's errors.

**Analytics did identification.** Matched controls, stratification and robust
regression answered "how much, and is it real?" This had to stay interpretable:
a score that affects a driver's pay must be explainable to that driver.

**AI extends it in three places analytics cannot reach.**

Scale: our manoeuvre detector needs 10 Hz video-derived trajectories. Real fleet
telematics is 1 Hz consumer GPS. A sequence model trained on NGSIM as labelled
ground truth can recognise the same manoeuvres in noisy production data.

Counterfactual precision: instead of matching each event to similar vehicles, a
trajectory model can predict what *that specific follower's* speed would have
been absent the cut-in — a per-event counterfactual rather than a group average.

Discovery: clustering driver trajectories surfaces behavioural patterns we did
not think to hypothesise.

Critically, analytics **validates** the AI. We would check the learned
counterfactual against the matched-control estimate on held-out data. Without
that check the model is unfalsifiable — and our own experience is the argument:
a plausible-looking specification error reversed our headline result's sign.
