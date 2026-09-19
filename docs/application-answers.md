# Smart Logistics Datathon 2026 — 報名三題答案

**英文是要送出去的版本。中文是給你看的對照，不要貼進表單。**

字數上限每題 200 字，由 `scripts/check_answer_length.py` 檢查（目前 196 / 185 / 183）。

送出前用這個指令再確認一次：

```bash
python scripts/check_answer_length.py
```

---

# Q1

> Describe one or two projects undertaken by your team members that relate to
> logistics, supply chain management, or data analytics.
>
> 請描述你的隊員做過的一到兩個與物流、供應鏈管理或資料分析相關的專案。

## 英文（送出這份）

We built *The Externality of a Lane Change*, an open-source analysis of 8.7
million vehicle-trajectory records from the US DOT's NGSIM programme: when a
vehicle changes lanes, what does it cost the traffic behind it, and does a
truck cost more?

We detected 2,472 clean lane changes, measured the follower's speed loss and
recovery, and compared each against matched moments where no lane change
occurred, paired on pre-event speed, acceleration trend and headway.

We expected trucks to impose a larger cost. The data rejected it. Truck cut-ins
cost the follower 1.62 km/h *less* than car cut-ins
(95% CI −3.12 to −0.02), and controlling for traffic state, vehicle class is
indistinguishable from zero (p = 0.47). What survives is congestion: every
1 km/h slower the surrounding traffic, the same manoeuvre costs 0.35 km/h more
(p < 0.001). The externality belongs to the moment, not the vehicle.

Four data defects surfaced, one reversing the headline's sign; all documented
publicly.

We are two final-year Information Management students at NCCU. One of us led the
matched-control identification strategy, the other the service and commercial
framing — so this runs from trajectories through to a costed service concept,
not just statistics.

## 中文對照

我們做了《變換車道的外部成本》，這是一份開源分析，使用美國運輸部 NGSIM 計畫的
870 萬筆車輛軌跡資料，要問的是：當一台車變換車道時，它讓後方的車流付出多少代
價？貨車付出的代價會比較大嗎？

我們偵測出 2,472 次乾淨的變換車道事件，量測後車的速度損失與恢復狀況，並將每一
次事件與「沒有發生換道、但條件相同的時刻」做對照——依據事前的速度、加速趨勢與
車距進行配對。

我們原本預期貨車造成的代價比較大。資料推翻了這個假設。貨車切入讓後車付出的代價
反而比小客車**少** 1.62 km/h（95% 信賴區間 −3.12 到 −0.02）；而且在控制路況之後，
車種的影響與零沒有統計上的差別（p = 0.47）。真正撐得住的是壅塞程度：周圍車流每
慢 1 km/h，同一個動作就讓後車多付出 0.35 km/h 的代價（p < 0.001）。**外部成本屬
於「時機」，不屬於「車種」。**

過程中出現四個資料缺陷，其中一個讓結論的正負號反轉；全部都公開記錄。

我們是兩位政大資訊管理系四年級學生。一位主導對照組的因果識別策略，另一位主導服
務與商業框架——所以這份專案是從原始軌跡一路做到有定價的服務構想，而不只是統計。

---

# Q2

> Drawing on a project described above, how may it be packaged as a "service"
> and what may make the service "smart"?
>
> 根據上述專案，它可以如何被包裝成一項「服務」？什麼會讓這項服務變得「智慧」？

## 英文（送出這份）

The finding productises as a **Congestion Externality Score** for fleet
operators: an API consuming the GPS traces operators already collect for
compliance and insurance, returning, per driver and per route, how much
disturbance their manoeuvres imposed on surrounding traffic.

Existing telematics scores — harsh braking, speeding, idling — all measure risk
to the driver's *own* vehicle. None price the disturbance paid for by everyone
else. It is invisible to the driver, because it happens behind them.

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

## 中文對照

這個發現可以直接產品化為給車隊業者的**壅塞外部成本評分（Congestion Externality
Score）**：一個 API，吃進業者為了法規遵循與保險本來就已經在蒐集的 GPS 軌跡，回傳
每位駕駛、每條路線造成了多少對周圍車流的擾動。

現有的車隊 telematics 評分——急煞、超速、怠速——量的全都是對**駕駛自己車輛**的
風險。沒有任何一項在為**其他所有人承受的擾動**定價。這個代價對駕駛是看不見的，
因為它發生在他後面。

有三件事讓它是「智慧」的，而不只是「自動化」。

**第一，它依情境定價，不是死規則。** 我們的迴歸顯示，周圍車流每慢 1 km/h，同一個
動作就多造成 0.35 km/h 的代價。所以評分會用實測的路況為每個事件加權，而不是套一
個固定罰分。

**第二，它的標竿是已被觀測到的行為，不是抽象理想值。** 在我們的資料裡，職業駕駛
造成的代價本來就比一般小客車駕駛低——所以目標是一個真實存在的標準。

**第三，它會閉環。** 教練式輔導改變行為 → 改變被重新量測 → 模型被重新估計。所以
這個服務是在「學習」對每個車隊什麼真正有效，而不是「宣稱」什麼有效。

---

# Q3

> Based on the same project experience, explain how Artificial Intelligence (AI)
> and data analytics work together to further enhance the project results?
>
> 根據同一個專案經驗，說明人工智慧（AI）與資料分析如何協同運作，進一步提升專案
> 成果？

## 英文（送出這份）

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

## 中文對照

在我們的專案裡，這兩者做的是不同的工作，而且互相抓出對方的錯誤。

**資料分析負責「識別」。** 配對對照組、分層、穩健迴歸，回答的是「有多大，以及它
是不是真的？」這部分必須維持可解釋——一個會影響駕駛薪酬的評分，必須能對那位駕駛
解釋清楚。

**AI 則延伸到三個資料分析到不了的地方。**

**規模化：** 我們現在的動作偵測器需要 10 Hz、從影像判讀出來的軌跡。真實車隊只有
1 Hz 的消費級 GPS。用 NGSIM 當作有標準答案的訓練資料來訓練序列模型，就能在充滿
雜訊的實務資料中辨識出同樣的動作。

**反事實的精確度：** 與其把每個事件配對到條件相似的車輛，軌跡模型可以直接預測
**那一台特定後車**在沒有被切入的情況下速度會是多少——這是逐事件的反事實，而不是
群體平均。

**發現：** 對駕駛軌跡做分群，能浮現出我們根本沒想到要去假設的行為模式。

**關鍵在於，資料分析會「驗證」AI。** 我們會拿模型學出來的反事實，在留存資料上跟
配對法的估計做比對。沒有這個檢查，模型是不可證偽的——而我們自己的經驗就是最好的
論證：一個看起來完全合理的模型設定錯誤，曾經讓我們結論的正負號整個反轉。
