# Methodology

How a raw 10 Hz trajectory table becomes a number you can defend in a Q&A.

---

## 0. Units

NGSIM publishes in US customary units. Everything is converted once, in
`src/ngsim.py`, and never again:

| Field | Raw unit | Used as |
|---|---|---|
| `local_y`, `space_headway` | feet | metres where reported |
| `v_vel` | feet / second | km/h (`× 1.09728`) |
| `frame_id` | 10 Hz counter | seconds (`× 0.1`) |

## 1. Building clean trajectories

**Deduplication.** The published table contains exact duplicate rows —
704,000 of US-101's 4,802,933 (14.7%) are byte-for-byte repeats. They are
dropped on load; because they are identical in every column this loses nothing,
but leaving them in would double-weight those vehicles in every average.

**Trajectory key.** `vehicle_id` is *not* unique. Each site is three
concatenated 15-minute recordings and both `vehicle_id` and `frame_id` restart
in each. A recording's clock origin, `global_time − frame_id × 100`, is
constant within a recording and different between recordings, so that is the
period key; both sites resolve to exactly three values. Every trajectory is
keyed on `(site, period, vehicle_id)`.

Cutting on gaps in `global_time` instead — the obvious approach — fails
silently: I-80's 17:00–17:15 and 17:15–17:30 recordings are contiguous, so
there is no gap between them, and 88 vehicle IDs collide. Skipping this step
splices unrelated vehicles together and manufactures lane changes that never
happened.

**Mainline only.** Only through-lanes are kept (I-80 lanes 1–6, US-101 lanes
1–5). Higher lane numbers are on-ramps, off-ramps and auxiliary merge lanes,
where a lane change is a *forced merge* — a different behaviour with a different
cause, which would contaminate a study of discretionary manoeuvres.

**Smoothing.** Speed is smoothed with a centred 11-frame (1.1 s) moving average
within each trajectory before any statistic is computed. NGSIM speeds are
differentiated from video-extracted positions and carry substantial
high-frequency noise. 1.1 s is long enough to suppress that noise and short
enough to leave a genuine braking response intact.

## 2. Detecting a lane change

A candidate event is any frame where a vehicle's `lane_id` differs from its
previous frame's.

Two filters turn candidates into events:

1. **Stability, 3 s each side.** The vehicle must have held the origin lane for
   ≥ 3 s before and hold the target lane for ≥ 3 s after. This removes detector
   flicker (a one-frame lane flip that is a tracking artefact, not a manoeuvre)
   and weaving (three changes in four seconds counted as three independent
   events).
2. **A follower must exist.** NGSIM's own `following` field names the vehicle
   directly behind, in the same lane. Read just after the change, this is the
   vehicle that inherited the lane-changer — the party that pays the cost. Events
   with no follower are dropped; there is nobody to measure.

## 3. Measuring what the follower pays

All windows are relative to the change at `t = 0`:

| Window | Span | Purpose |
|---|---|---|
| Baseline | −4.0 s … −1.0 s | the follower's undisturbed speed |
| Response | 0 … +5.0 s | where the slowdown happens |
| Recovery | 0 … +10.0 s | how long until it is over |

The baseline stops 1 s *before* the change, not at the change itself: a driver
who sees a truck signalling often lifts off before the wheels cross the line, and
including that anticipation in the baseline would understate the effect.

Reported per event:

- **`drop_kmh`** — baseline speed minus the minimum speed in the response window.
- **`drop_pct`** — the same as a share of baseline, so a 5 km/h drop at 20 km/h
  is not treated as equivalent to 5 km/h at 90 km/h.
- **`recovery_s`** — time from the speed minimum until speed returns to 95% of
  baseline. **Right-censored at 10 s** and flagged as such. Because NGSIM's
  sections are short (~500 m on I-80), some followers leave the section before
  recovering, so the reported recovery time is a *lower bound*.

Events whose baseline speed is essentially zero are dropped: "slowing down" is
not a meaningful measurement on a vehicle that was already stopped.

## 4. The control group

**This is the step that makes the result mean anything.**

Measuring a speed drop after a lane change does not show the lane change caused
it. Congested traffic oscillates; pick a random moment and the vehicle is often
decelerating anyway.

So the same measurement is taken at **matched moments where no lane change
occurred**: a vehicle that held one lane across the entire −4 s … +10 s window,
so nothing cut in front of it. Candidates are thinned to one every 0.5 s
(adjacent frames of the same vehicle are near-duplicate windows and would fake
precision), measured exactly like real events, then matched by **nearest
neighbour without replacement**, within site × congestion regime, on three
standardised covariates:

| covariate | why |
|---|---|
| `baseline_kmh` | how fast the vehicle was going |
| `pre_trend_kmh` | whether it was already speeding up or slowing down |
| `headway_pre_ft` | how much room it had in front |

**All three are measured strictly before t = 0.** Two design points that each
changed the answer:

- **`pre_trend_kmh` is not optional.** Matching on speed level alone, in
  stop-and-go traffic, selects vehicles accelerating out of a wave — which
  cannot decelerate much further. The resulting control group rose 23% over the
  window and was structurally unable to show the effect (decision log D8).
- **The gap at t = 0 must be excluded.** A cut-in is *defined* by the gap
  shrinking, so `headway_at_t` is post-treatment. Matching on it matches away
  the mechanism, and flipped the headline estimate from +0.76 km/h to
  −0.35 km/h (decision log D10).

Matching is without replacement so no single quiet moment anchors many events.
Three controls are drawn per event. **The reported externality is the difference
between the two groups**, not the raw post-event drop.

### Checking the match rather than assuming it

Two checks run on every result:

1. **Pre-event traces must coincide.** Plotted over the window, the control and
   event mean speed traces are indistinguishable until t = 0 (`fig1`).
2. **The cut-in must be visible in a column the estimator never sees.** Event
   followers lose 42.6 ft of headway at t = 0 (106.3 → 63.7); matched controls
   lose 3.2 ft (105.8 → 102.7). The events really are cut-ins and the controls
   really are undisturbed.

## 5. Congestion regime

Regime is *measured*, not read off the clock. Each lane is divided into 30 s
cells, the mean speed of all vehicles in the cell is computed, and the cell is
labelled `heavy` below 25 km/h and `light` above.

25 km/h, not the textbook 40: both NGSIM freeway sites were recorded in the
peak, local mean speed spans roughly 5–47 km/h with a median near 24, and a
40 km/h cut would label 99% of the sample congested and leave the comparison
empty. The cut point is chosen to split *this* data, and is stated rather than
implied.

A speed-based definition was chosen over "peak / off-peak by recording time"
because it is reproducible on any other dataset. That matters: the service
concept this analysis supports has to run on live fleet telematics, where there
is no NGSIM period label — only speed.

The binary split is for presentation only. The regression in §6 uses the
continuous local mean speed.

## 6. Separating the truck effect from where trucks drive

A raw truck-versus-car gap could simply reflect *where and when* trucks change
lanes — right-hand lanes, denser traffic, lower speeds. An OLS regression with
heteroskedasticity-robust (HC3) standard errors holds those constant:

```
drop_kmh ~ is_truck + local_mean_kmh + is_truck:local_mean_kmh
           + baseline_kmh + space_headway + site
```

Congestion enters **continuously**, as the measured local mean speed, rather
than as a threshold dummy: the question is whether the cost grows as traffic
slows, and a dummy discards most of that variation. The
`is_truck:local_mean_kmh` interaction answers "does congestion amplify the truck
difference?" directly, rather than by eyeballing two subgroup means.

This regression is what turned the raw truck difference into the actual finding.
The unadjusted truck gap is -1.62 km/h; adjusted, the truck coefficient is
-1.36 km/h with p = 0.47, while `local_mean_kmh` is -0.351 km/h per km/h with
p < 0.001. The vehicle class does not survive the controls. The traffic state
does.

## 7. Uncertainty

Every difference is reported with a **bootstrap 95% confidence interval**
(5,000 resamples, fixed seed `20260919`), not as a bare point estimate. The truck
sample is small — **54 truck events against 2,418 car events** — and a point
estimate would imply a precision the data does not have. The truck result is
reported because it contradicts the project's own hypothesis, not because it is
precise.

## 8. What this design cannot do

- It is **observational**. Matching and regression remove obvious confounders;
  they do not make it a randomised experiment.
- Recovery times are **censored** by the length of the observed section.
- The data is **2005 US freeway traffic**. The method transfers to a 2026 Hong
  Kong fleet; the coefficients should be re-estimated locally before anyone acts
  on them.
