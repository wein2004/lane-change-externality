# Decision Log

Every non-obvious choice in this project, with the reasoning behind it. Kept so a
reader (or a judge) can audit *why* the analysis looks the way it does, not just
what it produced.

---

## D1 — Topic: truck vs. car lane-change externality (2026-09-19)

**Considered:** a generic "how much does one lane change cost the traffic behind
it?" study on NGSIM I-80.

**Rejected because:** the target competition (CUHK Smart Logistics Datathon 2026,
theme *AI-Driven Horizons for Logistics Intelligence*) scores applications on
relevance first. A generic freeway lane-change study is traffic engineering, not
logistics; the link to logistics would have to be asserted in prose rather than
shown in the data. Originality was also weak — single lane-change impact has an
established literature.

**Chosen instead:** split every lane-change event by the *vehicle class of the
lane-changer*, using NGSIM's `v_class` field (1 = motorcycle, 2 = auto,
3 = truck). Trucks are the logistics vehicles. The research question becomes:

> Does a heavy goods vehicle changing lanes impose a larger cost on the traffic
> behind it than a passenger car does — and does that gap widen under congestion?

This makes the logistics relevance structural rather than rhetorical, and the
question is not one the existing NGSIM lane-change literature commonly answers.

**Known cost of this choice:** trucks are only ~3.7% of I-80 rows
(169,132 of 4,566,387). The truck event sample will be small. Mitigations: pool
I-80 with US-101, and report confidence intervals honestly rather than point
estimates.

---

## D2 — Sites: freeways only, arterials excluded (2026-09-19)

NGSIM contains four sites. We use **I-80** (Emeryville, CA) and **US-101** (Los
Angeles, CA) and exclude **Lankershim Blvd** and **Peachtree St**.

Both excluded sites are signalised arterials. A follower decelerating there is
usually reacting to a red light, not to the vehicle that just cut in front of it.
Including them would inflate the measured impact with signal-induced stops.

---

## D3 — A control group is mandatory (2026-09-19)

The naive measurement — "follower speed drops X km/h after a lane change" — is
not evidence that the lane change *caused* the drop. Congested freeway traffic
oscillates constantly; a follower would have decelerated at many randomly chosen
moments too.

So every real lane-change event is compared against **matched pseudo-events**:
moments where no lane change occurred within ±5 s in that lane, drawn to match
the real event on speed bin, space headway bin, site and congestion regime. The
reported effect is the *difference* between the two.

This is the main methodological differentiator of the project and is cheap to
implement. Without it the headline number is not defensible under questioning.

---

## D4 — Data quality: NGSIM noise is a known, documented problem (2026-09-19)

NGSIM velocities and accelerations are derived by numerical differentiation of
positions that were themselves extracted from video, and the resulting
acceleration series contain physically impossible values. This is well
documented (Punzo, Borzacchiello & Ciuffo, 2011, *On the assessment of vehicle
trajectory data accuracy*, Transportation Research Part C).

We therefore (a) smooth speed with a symmetric moving average before computing
any speed statistic, (b) prefer speed-based measures over acceleration-based
ones, and (c) state the limitation explicitly rather than hiding it. Naming a
known flaw in your own data source is a credibility gain, not a loss.

---

## D5 — Vehicle IDs are not unique across recordings (2026-09-19)

Each NGSIM site is published as three concatenated 15-minute recordings, and
`vehicle_id` restarts from 1 in each. Grouping by `vehicle_id` alone splices
unrelated vehicles into one trajectory and manufactures lane changes that never
happened.

**First attempt, and why it failed.** Periods were cut on gaps in `global_time`
larger than 60 s. That works on most of the data and fails silently on I-80:
its 17:00-17:15 and 17:15-17:30 recordings are *contiguous* in wall-clock time,
so there is no gap to cut on. The two merged into a single period, 88 vehicle
IDs collided, and the pipeline only surfaced it as a downstream
`cannot handle a non-unique multi-index!` — not as anything resembling the
actual problem.

**The fix.** `frame_id` also restarts in each recording, so the recording's
clock origin

    epoch = global_time - frame_id * 100

is exactly constant within a recording and different between recordings. Both
sites resolve to exactly three distinct epoch values, matching the three
published recordings. Every trajectory is keyed on
`(site, period, vehicle_id)`.

`tests/test_detection.py::test_contiguous_recordings_are_still_split` pins this:
it builds two recordings with *zero* gap between them and asserts they still
separate.

**Method note:** the gap heuristic was a guess about how the data is laid out.
The epoch key is a property the data actually has. Prefer the second kind.

---

## D6 — Congestion regime is measured, not assumed (2026-09-19)

Rather than labelling recording periods "peak" and "off-peak" by their clock
time, we classify each event by the **measured mean speed of the surrounding
traffic** in a rolling spatial-temporal window. A speed-based regime definition
is reproducible on any other dataset, which matters because the service concept
in the application answer has to work on live telematics data, not on NGSIM.

---

## D7 — Keyset pagination, not `$offset` (2026-09-19)

The first version of `scripts/01_download_ngsim.py` paged with Socrata's
`$offset`. On a 11.8M-row table this degrades badly: successive pages got
slower and slower and the download had produced no output after 18 minutes.

Rewritten to page on `vehicle_id` ranges (`WHERE vehicle_id >= lo AND
vehicle_id < hi`), which Socrata can serve from an index. Measured: 816,799
rows in 49 s, flat across the whole key range.

The script asserts that no single request reaches the row cap, because Socrata
truncates silently rather than erroring when a `$limit` is hit — a quiet
truncation would have removed whole vehicles from the sample without any
visible failure.

---

## D8 — The first control group was invalid; matching had to change (2026-09-19)

Caught by plotting the control group's mean speed trace instead of trusting its
summary statistic.

**What went wrong.** Controls were originally sampled within strata of
site × congestion regime × baseline-speed quintile. Plotted over the event
window, the control group's mean speed *rose 23%* while real event followers
stayed flat. Conditioning on speed level alone, in stop-and-go traffic, selects
vehicles that are accelerating out of a wave — and a vehicle already speeding up
cannot show much of a slowdown. The control group was structurally incapable of
exhibiting the effect it was supposed to bound, which biases the estimated
externality upward.

**The fix.** Controls are now built by **nearest-neighbour matching without
replacement**, inside site × regime, on three standardised covariates:

| covariate | why |
|---|---|
| `baseline_kmh` | how fast the vehicle was going |
| `pre_trend_kmh` | **whether it was already speeding up or slowing down** |
| `headway_at_t` | how much room it had in front |

`pre_trend_kmh` is the covariate that fixes the bias. `headway_at_t` matters
because the defining consequence of a cut-in is a suddenly smaller gap; without
it, controls would enjoy more room than any event follower ever does.

Matching without replacement stops one unusually quiet moment from anchoring
many events at once and understating the variance.

**Method note worth keeping:** the summary numbers looked plausible before and
after. Only the plot of the raw control trace exposed the problem. Every control
group in this project gets plotted, not just summarised.


---

## D9 — The published NGSIM table contains exact duplicate rows (2026-09-19)

Surfaced when the full US-101 run failed with
`cannot handle a non-unique multi-index!` after the D5 period fix had already
been applied.

**1,408,000 of US-101's 4,802,933 rows (29%) are byte-for-byte duplicates** of
another row — identical in every column, including `global_time`, `local_y` and
`v_vel`. 1,025 vehicles are affected.

They are dropped in `src/ngsim.py::load_site`. Because the duplicates are
identical in every field, dropping them loses nothing. Leaving them in would
have double-weighted a quarter of the US-101 vehicles in every mean, every
bootstrap resample and every matched control draw — and nothing in the output
would have looked wrong.

The dedup count is printed into `outputs/tables/02_detection_summary.md` on
every run rather than being silently applied.

**Method note:** two of this project's three data bugs (D5, D9) were invisible
in the summary statistics and only surfaced because an unrelated step happened
to crash. Neither would have changed the shape of a plausible-looking result
table. Assume a public dataset is dirty until a check says otherwise.


---

## D10 — Matching on the gap at t=0 was a bad control (2026-09-19)

The first nearest-neighbour matcher (D8) used three covariates:
`baseline_kmh`, `pre_trend_kmh`, and `headway_at_t` — the follower's gap to the
vehicle ahead **at the moment of the lane change**.

That third one is measured after treatment. A cut-in is *defined* by the gap
suddenly shrinking, so conditioning on it forces every control to share the
consequence of the treatment. It matches away the mechanism.

The effect was large enough to flip the sign of the headline result:

| | attributable excess speed drop |
|---|---|
| matching on `headway_at_t` (post-treatment) | **-0.35 km/h** (95% CI -0.69 .. -0.02) |
| matching on `headway_pre_ft` (pre-treatment) | **+0.76 km/h** (95% CI +0.44 .. +1.09) |

Matching now uses `headway_pre_ft`, the mean gap over the baseline window
(-4 s .. -1 s), which is entirely pre-treatment.

`headway_at_t` is still computed, but only as a **validation diagnostic**, and
it is a good one:

| | mean gap before | mean gap at t=0 | change |
|---|---|---|---|
| lane-change events | 106.3 ft | 63.7 ft | **-42.6 ft** |
| matched controls | 105.8 ft | 102.7 ft | -3.2 ft |

Event followers lose 42.6 ft of headway at t=0; matched controls lose 3.2 ft.
That is direct evidence the detected events really are cut-ins and the controls
really are undisturbed — from a column the estimator never sees.

---

## D11 — The hypothesis was wrong, and the paper says so (2026-09-19)

The project was designed around the hypothesis that heavy goods vehicles impose
a **larger** externality on following traffic than cars (D1). The data rejects
it, in the opposite direction:

- Truck-initiated lane changes cost the follower **1.62 km/h less** than
  car-initiated ones (95% CI -3.12 .. -0.02).
- The follower recovers **0.98 s faster** (95% CI -1.60 .. -0.30).
- Trucks change lanes **less often**: 7.7 vs 10.7 per vehicle-hour.
- Once traffic state, speed and headway are controlled for, the truck
  coefficient is **not statistically distinguishable from zero** (p = 0.47).

The last point is the interesting one. If the mechanism were mass and length —
"trucks are big, therefore disruptive" — the coefficient should survive the
controls. It does not. What survives is `local_mean_kmh`: every 1 km/h slower
the surrounding traffic, the same manoeuvre costs the follower 0.35 km/h more
(p < 0.001).

**The externality is a property of the moment, not of the vehicle.** The
headline, the README and the figure titles were rewritten to say that. The
original hypothesis is kept in this log rather than quietly deleted — a
pre-registered hypothesis that failed is evidence the analysis was not tuned
until it agreed with the authors.
