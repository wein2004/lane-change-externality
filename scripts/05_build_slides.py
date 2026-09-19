"""Write the deck files for the Slides artifact."""
from pathlib import Path
import json

ROOT = Path(__file__).parent / "deck"
(ROOT / "project" / "slides").mkdir(parents=True, exist_ok=True)

BG = "#FFFFFF"
INK = "#111111"
SUB = "#6B6B6B"
RULE = "#E4E4E4"
BLUE = "#2A78D6"
ORANGE = "#EB6834"
PANEL = "#F6F6F4"

SANS = "'Noto Sans TC', Arial, sans-serif"
MONO = "'JetBrains Mono', 'Courier New', monospace"

FIG1 = "/_blob/7fa453801f93c4f75c2a188288d91d09"
FIG2 = "/_blob/9aae5f643d22085e69d5a537d3f9355c"
FIG3 = "/_blob/62b61e757d7c84b97f8ec3409b22a158"

SEC = (f"background:{BG}; color:{INK}; font-family:{SANS}; "
       "padding:128px; display:flex; flex-direction:column")
SEC_FOOT = (f"background:{BG}; color:{INK}; font-family:{SANS}; "
            "padding:128px 128px 160px; display:flex; flex-direction:column")
SPREAD = "; justify-content:space-between"


def eyebrow(text):
    return (f'<p style="font-size:26px; font-weight:500; color:{SUB}; '
            f'letter-spacing:0.08em">{text}</p>')


def footer(text):
    return (f'<p style="position:absolute; left:128px; bottom:64px; '
            f'font-size:24px; color:{SUB}">{text}</p>')


def code_panel(lines, width=None):
    w = f"width:{width}px; " if width else ""
    rows = "".join(
        f'<p style="font-family:{MONO}; font-size:{l[1]}px; '
        f'color:{l[2]}; line-height:1.55; white-space:nowrap">{l[0]}</p>'
        for l in lines
    )
    return (f'<div style="{w}background:{PANEL}; padding:40px 48px; '
            f'border-left:4px solid {BLUE}; display:flex; '
            f'flex-direction:column">{rows}</div>')


def c(text, size=26, color=INK):
    return (text, size, color)


S = {}

# ---------------------------------------------------------------- cover --
S["cover"] = f'''<section id="cover" style="{SEC_FOOT}; justify-content:center; gap:40px">
  {eyebrow("資料分析專案 · NGSIM 車輛軌跡")}
  <h1 style="font-size:120px; font-weight:700; line-height:1.08">變換車道的<br>外部成本</h1>
  <p style="font-size:36px; color:{SUB}; line-height:1.5; width:1200px">一次換道，讓後方那台車付出多少代價？<br>誰付出得更多？</p>
  {footer("870 萬筆軌跡 · 2,472 次事件 · 開源可重現")}
  <aside>這是一份為 CUHK Smart Logistics Datathon 2026 報名而做的分析。重點不是結論漂亮，是方法站得住。</aside>
</section>'''

# --------------------------------------------------------------- thesis --
S["thesis"] = f'''<section id="thesis" data-transition="fade" style="{SEC}; justify-content:center; gap:48px">
  {eyebrow("假設與結果")}
  <h1 style="font-size:104px; font-weight:700; line-height:1.15; width:1520px">我們假設貨車<br>傷害更大。<br><span style="color:{ORANGE}">資料說相反。</span></h1>
  <p style="font-size:32px; color:{SUB}; line-height:1.6; width:1280px">而且控制路況之後，車種的影響與零沒有統計差別。</p>
  <aside>一個被自己資料推翻還照實寫的假設，是分析沒有被調整到符合作者期待的最強證據。</aside>
</section>'''

# ------------------------------------------------------------------ why --
S["why"] = f'''<section id="why" style="{SEC}{SPREAD}; gap:56px">
  <h2 style="font-size:72px; font-weight:700; line-height:1.15">為什麼問這個問題</h2>
  <div style="display:flex; gap:56px; align-items:start">
    <div style="width:700px; display:flex; flex-direction:column; gap:28px">
      <p style="font-size:32px; line-height:1.65; color:{INK}">車隊管理系統評分駕駛，評的全是<b>對自己車輛的風險</b>。</p>
      <p style="font-size:32px; line-height:1.65; color:{SUB}">沒有一項在評駕駛<b style="color:{INK}">對別人造成的代價</b>。那個代價駕駛看不到，因為它發生在他後面。</p>
    </div>
    <div style="flex:1; display:flex; flex-direction:column; gap:20px">
      <div style="background:{PANEL}; padding:32px 36px; display:flex; flex-direction:column; gap:8px">
        <h3 style="font-size:30px; font-weight:700">現有評分</h3>
        <p style="font-size:28px; color:{SUB}">急煞 · 超速 · 怠速 · 疲勞駕駛</p>
      </div>
      <div style="background:{BG}; padding:32px 36px; border:2px solid {BLUE}; display:flex; flex-direction:column; gap:8px">
        <h3 style="font-size:30px; font-weight:700; color:{BLUE}">沒有人在評的</h3>
        <p style="font-size:28px; color:{INK}">我的動作，讓後面的人付出多少？</p>
      </div>
    </div>
  </div>
  <aside>這一頁建立問題的商業正當性：它不是交通工程題，是車隊管理題。</aside>
</section>'''

# ----------------------------------------------------------------- data --
S["data"] = f'''<section id="data" style="{SEC_FOOT}{SPREAD}; gap:48px">
  <h2 style="font-size:72px; font-weight:700; line-height:1.15">資料：美國聯邦公路總署 NGSIM</h2>
  <p style="font-size:32px; color:{SUB}; line-height:1.6; width:1400px">架高攝影機逐格判讀真實高速公路車流，每秒 10 筆車輛位置。</p>
  <table style="font-family:{SANS}; font-size:30px; color:{INK}; padding:20px 24px; border:1px solid {RULE}">
    <tr style="background:{PANEL}">
      <th style="width:22%; text-align:left; font-weight:700">路段</th>
      <th style="width:26%; text-align:left; font-weight:700">地點</th>
      <th style="width:26%; text-align:right; font-weight:700">原始筆數</th>
      <th style="width:26%; text-align:right; font-weight:700">去重後</th>
    </tr>
    <tr><td>I-80</td><td>加州 Emeryville</td><td style="text-align:right">4,566,387</td><td style="text-align:right">4,566,387</td></tr>
    <tr><td>US-101</td><td>洛杉磯</td><td style="text-align:right">4,802,933</td><td style="text-align:right; color:{ORANGE}">4,098,933</td></tr>
  </table>
  <p style="font-size:30px; color:{INK}; line-height:1.6; width:1500px">US-101 有 <b style="color:{ORANGE}">704,000 筆逐位元完全重複</b>的資料列，佔 14.7%。留著會讓那些車在每個平均值裡被算兩次。</p>
  {footer("排除 Lankershim 與 Peachtree：有紅綠燈，後車減速是紅燈不是換道")}
  <aside>主動講資料缺陷是加分，不是扣分。</aside>
</section>'''

# ----------------------------------------------------------- sec-method --
S["sec-method"] = f'''<section id="sec-method" data-transition="push" style="{SEC}; justify-content:center; gap:32px">
  {eyebrow("01")}
  <h1 style="font-size:132px; font-weight:700; line-height:1.1">方法</h1>
  <p style="font-size:36px; color:{SUB}; line-height:1.5; width:1100px">怎麼從 870 萬筆軌跡，變成一個站得住的數字。</p>
</section>'''

# --------------------------------------------------------------- detect --
S["detect"] = f'''<section id="detect" style="{SEC}{SPREAD}; gap:48px">
  <h2 style="font-size:72px; font-weight:700; line-height:1.15">怎麼算一次「換道」</h2>
  <div style="display:flex; gap:64px; align-items:start">
    <div style="width:760px; display:flex; flex-direction:column; gap:24px">
      <div style="display:flex; flex-direction:column; gap:8px">
        <h3 style="font-size:32px; font-weight:700">穩定性：前後各滿 3 秒</h3>
        <p style="font-size:28px; color:{SUB}; line-height:1.6">擋掉偵測跳動與連續蛇行。</p>
      </div>
      <hr style="border-top:1px solid {RULE}">
      <div style="display:flex; flex-direction:column; gap:8px">
        <h3 style="font-size:32px; font-weight:700">必須有後車</h3>
        <p style="font-size:28px; color:{SUB}; line-height:1.6">沒有人承受代價，就沒有東西可量。</p>
      </div>
      <hr style="border-top:1px solid {RULE}">
      <div style="display:flex; flex-direction:column; gap:8px">
        <h3 style="font-size:32px; font-weight:700">只留主線車道</h3>
        <p style="font-size:28px; color:{SUB}; line-height:1.6">匝道上的「換道」是被迫匯入，成因不同。</p>
      </div>
    </div>
    <div style="flex:1; background:{PANEL}; padding:48px; display:flex; flex-direction:column; gap:24px">
      <h3 style="font-size:30px; font-weight:700; color:{SUB}">過濾漏斗</h3>
      <div style="display:flex; flex-direction:column; gap:18px">
        <p style="font-size:34px">原始換道　<b>4,031</b></p>
        <p style="font-size:34px">穩定性　　<b>2,955</b></p>
        <p style="font-size:34px">有後車　　<b>2,914</b></p>
        <p style="font-size:34px; color:{BLUE}">資料完整　<b>2,531</b></p>
      </div>
    </div>
  </div>
  <aside>漏斗每一層都寫進 outputs/tables/02_detection_summary.md，不是黑盒子。</aside>
</section>'''

# -------------------------------------------------------------- control --
S["control"] = f'''<section id="control" style="{SEC}{SPREAD}; gap:40px">
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">對照組決定結論算不算數</h2>
  <div style="display:flex; gap:56px; align-items:center">
    <div style="width:720px; display:flex; flex-direction:column; gap:24px">
      <p style="font-size:30px; line-height:1.65; color:{SUB}">「換道後掉了 3.9 km/h」什麼都沒證明——塞車車流本來就在不停忽快忽慢。</p>
      <p style="font-size:30px; line-height:1.65">所以每筆事件都對照<b>沒有換道、但條件相同</b>的時刻，用最近鄰配對三個<b style="color:{BLUE}">事前</b>變數：</p>
      <div style="display:flex; flex-direction:column; gap:12px">
        <p style="font-size:28px">原本開多快</p>
        <p style="font-size:28px">原本在加速還是減速</p>
        <p style="font-size:28px">前方原本有多少空間</p>
      </div>
    </div>
    <img src="{FIG1}" alt="後車速度曲線：對照組與事件組在換道前完全重疊，之後分開" style="flex:1; height:520px; object-fit:contain; background:{PANEL}">
  </div>
  <p style="font-size:30px; color:{INK}; line-height:1.6">兩條曲線在換道前<b>完全重疊</b>，之後才分開。這就是配對有效的視覺證據。</p>
  <aside>這張圖是整份專案最該先給人看的一張。</aside>
</section>'''

# ----------------------------------------------------------- code-match --
code_lines = [
    c("# 最近鄰配對，不重複取樣，在同路段 × 同壅塞程度之內", 26, SUB),
    c('cols = ["baseline_kmh", "pre_trend_kmh", "headway_pre_ft"]', 28),
    c("", 28),
    c("mu, sd = c_raw.mean(axis=0), c_raw.std(axis=0)", 28),
    c("tree   = cKDTree((c_raw - mu) / sd)", 28),
    c("_, nn  = tree.query((e_raw - mu) / sd, k=k)", 28),
    c("", 28),
    c("# headway_at_t 刻意不放進來：它是 treatment 之後的變數", 26, ORANGE),
    c("# 被切入的定義就是車距變小，配它等於把機制配掉", 26, ORANGE),
]
S["code-match"] = f'''<section id="code-match" style="{SEC_FOOT}{SPREAD}; gap:40px">
  {eyebrow("scripts/02_detect_events.py")}
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">配對的三個變數，全部在事件發生前量測</h2>
  {code_panel(code_lines)}
  <p style="font-size:30px; line-height:1.6; color:{INK}; width:1500px">第一版用了「換道當下的車距」。那是事後變數，<b style="color:{ORANGE}">它把結論的正負號翻了過來</b>：−0.35 變成 +0.76。</p>
  {footer("完整理由：docs/decision-log.md D10")}
  <aside>一個看起來完全合理的變數選擇，就能翻轉結論。這是整份專案最值錢的一段。</aside>
</section>'''

# ------------------------------------------------------------- validate --
S["validate"] = f'''<section id="validate" style="{SEC_FOOT}{SPREAD}; gap:44px">
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">用估計式沒看過的欄位驗證配對</h2>
  <p style="font-size:32px; color:{SUB}; line-height:1.6; width:1500px">車距沒有進入配對，所以它是獨立的檢查，不是循環論證。</p>
  <table style="font-family:{SANS}; font-size:32px; color:{INK}; padding:24px 28px; border:1px solid {RULE}">
    <tr style="background:{PANEL}">
      <th style="width:34%; text-align:left; font-weight:700"></th>
      <th style="width:22%; text-align:right; font-weight:700">事前車距</th>
      <th style="width:22%; text-align:right; font-weight:700">換道當下</th>
      <th style="width:22%; text-align:right; font-weight:700">變化</th>
    </tr>
    <tr><td>換道事件</td><td style="text-align:right">106.3 ft</td><td style="text-align:right">63.7 ft</td><td style="text-align:right; color:{ORANGE}">−42.6 ft</td></tr>
    <tr><td>配對對照組</td><td style="text-align:right">105.8 ft</td><td style="text-align:right">102.7 ft</td><td style="text-align:right">−3.2 ft</td></tr>
  </table>
  <p style="font-size:32px; line-height:1.6; width:1500px">這證明兩件事：我們抓到的真的是<b>切入</b>，而對照組真的<b>沒被干擾</b>。</p>
  {footer("事前三個配對變數的平均值：30.86 vs 30.90、1.62 vs 1.61、106.3 vs 105.8")}
</section>'''

# ----------------------------------------------------------- sec-result --
S["sec-result"] = f'''<section id="sec-result" data-transition="push" style="{SEC}; justify-content:center; gap:32px">
  {eyebrow("02")}
  <h1 style="font-size:132px; font-weight:700; line-height:1.1">結果</h1>
  <p style="font-size:36px; color:{SUB}; line-height:1.5; width:1100px">2,472 次事件，7,591 個配對對照組。</p>
</section>'''

# ------------------------------------------------------------------ r1 --
S["r1"] = f'''<section id="r1" style="{SEC}{SPREAD}; gap:40px">
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">換道確實有代價</h2>
  <div style="display:flex; gap:56px; align-items:center">
    <div style="width:700px; display:flex; flex-direction:column; gap:36px">
      <div style="display:flex; flex-direction:column; gap:8px">
        <p style="font-size:30px; color:{SUB}">後車多掉的速度</p>
        <h3 style="font-size:88px; font-weight:700; color:{BLUE}">+0.76 km/h</h3>
        <p style="font-size:28px; color:{SUB}">95% 信賴區間 +0.44 ～ +1.09</p>
      </div>
      <hr style="border-top:1px solid {RULE}">
      <div style="display:flex; flex-direction:column; gap:8px">
        <p style="font-size:30px; color:{SUB}">恢復時間延遲</p>
        <h3 style="font-size:88px; font-weight:700; color:{BLUE}">+0.27 秒</h3>
        <p style="font-size:28px; color:{SUB}">95% 信賴區間 +0.15 ～ +0.40</p>
      </div>
    </div>
    <img src="{FIG2}" alt="不同路況下後車速度損失長條圖，含信賴區間" style="flex:1; height:600px; object-fit:contain; background:{PANEL}">
  </div>
  <aside>都是相對於配對對照組的差值，不是原始掉幅。</aside>
</section>'''

# ------------------------------------------------------------------ r2 --
S["r2"] = f'''<section id="r2" style="{SEC_FOOT}{SPREAD}; gap:40px">
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">但貨車的代價<span style="color:{ORANGE}">更低</span>，不是更高</h2>
  <img src="{FIG3}" alt="貨車減小客車的差異點圖，三種路況，含 95% 信賴區間" style="width:1664px; height:400px; object-fit:contain; background:{PANEL}">
  <div style="display:flex; gap:40px">
    <p style="flex:1; font-size:30px; line-height:1.6">貨車切入讓後車少掉 <b>1.62 km/h</b>，恢復也快 <b>0.98 秒</b>。</p>
    <p style="flex:1; font-size:30px; line-height:1.6; color:{SUB}">而且貨車換道次數本來就比較少：每車小時 7.7 次 vs 10.7 次。</p>
  </div>
  {footer("貨車事件僅 54 筆，對小客車 2,418 筆——所以全部報信賴區間，不報點估計")}
  <aside>樣本薄要主動講。這個結果值得注意是因為它推翻了我們自己的假設，不是因為它精確。</aside>
</section>'''

# ---------------------------------------------------------- regression --
S["regression"] = f'''<section id="regression" style="{SEC_FOOT}{SPREAD}; gap:40px">
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">控制之後，撐下來的是路況</h2>
  <table style="font-family:{SANS}; font-size:30px; color:{INK}; padding:18px 24px; border:1px solid {RULE}">
    <tr style="background:{PANEL}">
      <th style="width:46%; text-align:left; font-weight:700">變數</th>
      <th style="width:20%; text-align:right; font-weight:700">係數</th>
      <th style="width:16%; text-align:right; font-weight:700">p 值</th>
      <th style="width:18%; text-align:left; font-weight:700"></th>
    </tr>
    <tr><td>是否為貨車</td><td style="text-align:right">−1.364</td><td style="text-align:right">0.468</td><td style="color:{SUB}">不顯著</td></tr>
    <tr style="background:{PANEL}"><td><b>周圍車流平均速度</b></td><td style="text-align:right"><b>−0.351</b></td><td style="text-align:right">9e-67</td><td style="color:{BLUE}"><b>高度顯著</b></td></tr>
    <tr><td>後車原本速度</td><td style="text-align:right">+0.470</td><td style="text-align:right">1e-151</td><td style="color:{SUB}">顯著</td></tr>
    <tr><td>車距</td><td style="text-align:right">−0.035</td><td style="text-align:right">3e-24</td><td style="color:{SUB}">顯著</td></tr>
  </table>
  <p style="font-size:32px; line-height:1.6; width:1560px">如果機制是「貨車又大又重」，車種係數應該撐得過控制變數。<b>它沒有。</b>撐過去的是路況：周圍車流每慢 1 km/h，同一動作多造成 0.35 km/h 的擾動。</p>
  {footer("OLS，HC3 穩健標準誤，壅塞以連續變數進入")}
</section>'''

# ------------------------------------------------------------ takeaway --
S["takeaway"] = f'''<section id="takeaway" data-transition="fade" style="{SEC}; justify-content:center; gap:48px">
  {eyebrow("核心結論")}
  <h1 style="font-size:112px; font-weight:700; line-height:1.18; width:1560px">外部成本屬於<br><span style="color:{BLUE}">「時機」</span>，<br>不屬於「車種」。</h1>
  <p style="font-size:34px; color:{SUB}; line-height:1.6; width:1400px">針對車種的管制瞄錯了變數。針對「什麼時候、切進多大的縫」才是對的。</p>
  <aside>這句話是整份簡報的目的地。前面每一頁都是為了讓它站得住。</aside>
</section>'''

# -------------------------------------------------------------- honest --
S["honest"] = f'''<section id="honest" style="{SEC_FOOT}{SPREAD}; gap:44px">
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">我們也報了對自己不利的數字</h2>
  <div style="display:flex; gap:24px">
    <div style="flex:1; background:{PANEL}; padding:40px; display:flex; flex-direction:column; gap:12px">
      <p style="font-size:28px; color:{SUB}">凹陷深度</p>
      <h3 style="font-size:56px; font-weight:700">+0.76 km/h</h3>
      <p style="font-size:26px; color:{BLUE}">顯著</p>
    </div>
    <div style="flex:1; background:{PANEL}; padding:40px; display:flex; flex-direction:column; gap:12px">
      <p style="font-size:28px; color:{SUB}">恢復時間</p>
      <h3 style="font-size:56px; font-weight:700">+0.27 秒</h3>
      <p style="font-size:26px; color:{BLUE}">顯著</p>
    </div>
    <div style="flex:1; background:{BG}; padding:40px; border:2px solid {ORANGE}; display:flex; flex-direction:column; gap:12px">
      <p style="font-size:28px; color:{SUB}">後車淨損失時間</p>
      <h3 style="font-size:56px; font-weight:700">+0.03 秒</h3>
      <p style="font-size:26px; color:{ORANGE}">信賴區間跨過 0</p>
    </div>
  </div>
  <p style="font-size:32px; line-height:1.65; width:1560px">擾動是<b>尖銳而短暫</b>的，不是持續的損失。我們的分析<b style="color:{ORANGE}">不支持</b>「一次換道讓後車損失可測量的行車時間」，我們也沒有這樣寫。</p>
  {footer("擾動會不會向上游放大成連鎖壅塞，這份資料的路段只有 500–640 公尺，答不了")}
  <aside>誠實報告不利數字，是這份分析可信度的來源。不要為了好看拿掉這一頁。</aside>
</section>'''

# ---------------------------------------------------------------- bugs --
S["bugs"] = f'''<section id="bugs" style="{SEC_FOOT}{SPREAD}; gap:40px">
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">四個 bug，三個在摘要統計上看不出來</h2>
  <table style="font-family:{SANS}; font-size:28px; color:{INK}; padding:18px 22px; border:1px solid {RULE}">
    <tr style="background:{PANEL}">
      <th style="width:10%; text-align:left; font-weight:700"></th>
      <th style="width:56%; text-align:left; font-weight:700">問題</th>
      <th style="width:34%; text-align:left; font-weight:700">怎麼被發現的</th>
    </tr>
    <tr><td>D5</td><td>兩段錄影時間連續，切不開，88 個車號撞號</td><td style="color:{SUB}">不相干的當機</td></tr>
    <tr><td>D8</td><td>第一版對照組在整個視窗內加速 23%</td><td style="color:{BLUE}">把曲線畫出來</td></tr>
    <tr><td>D9</td><td>官方資料有 704,000 筆完全重複的資料列</td><td style="color:{SUB}">不相干的當機</td></tr>
    <tr style="background:{PANEL}"><td>D10</td><td><b>配對用了事後變數，結論正負號翻掉</b></td><td style="color:{BLUE}">想清楚因果順序</td></tr>
  </table>
  <p style="font-size:30px; color:{SUB}; line-height:1.6; width:1560px">每一個決策與每一個錯誤都寫進公開的 decision log，共 11 條。</p>
  {footer("docs/decision-log.md")}
</section>'''

# ----------------------------------------------------------- code-test --
test_lines = [
    c("$ python tests/test_detection.py", 28, SUB),
    c("", 28),
    c("  PASS  單格跳動被穩定性過濾擋掉", 28),
    c("  PASS  連續蛇行被擋掉", 28),
    c("  PASS  注入的減速幅度量得出來", 28),
    c("  PASS  不恢復的情況正確標記為截斷", 28),
    c("  PASS  時間上連續的兩段錄影仍然被切開", 28, BLUE),
    c("", 28),
    c("all checks passed", 28, BLUE),
]
S["code-test"] = f'''<section id="code-test" style="{SEC_FOOT}{SPREAD}; gap:40px">
  {eyebrow("tests/test_detection.py")}
  <h2 style="font-size:64px; font-weight:700; line-height:1.15">22 項合成軌跡檢驗</h2>
  <div style="display:flex; gap:48px; align-items:start">
    {code_panel(test_lines, width=900)}
    <div style="flex:1; display:flex; flex-direction:column; gap:24px">
      <p style="font-size:30px; line-height:1.65">用手工造的軌跡測核心邏輯——答案是我們自己造的，所以已知。</p>
      <p style="font-size:30px; line-height:1.65; color:{SUB}">藍色那一項是 D5 那個 bug 的<b style="color:{INK}">回歸測試</b>：確保它不會再發生。</p>
    </div>
  </div>
  {footer("每次 run_all.sh 都會先跑測試，不過就不繼續")}
</section>'''

# --------------------------------------------------------------- repro --
S["repro"] = f'''<section id="repro" data-transition="fade" style="{SEC_FOOT}; justify-content:center; gap:44px">
  {eyebrow("可重現性")}
  <h1 style="font-size:96px; font-weight:700; line-height:1.15; width:1520px">重跑一次，<br>每個數字都一樣。</h1>
  <p style="font-size:32px; color:{SUB}; line-height:1.65; width:1400px">連 bootstrap 信賴區間到小數點後兩位都相同——固定亂數種子。</p>
  {code_panel([c("$ bash scripts/run_all.sh", 32, INK)], width=760)}
  {footer("下載 → 偵測事件 → 建對照組 → 統計 → 圖表 → 字數檢查")}
  <aside>可重現性不是加分項，是這份分析能被檢驗的前提。</aside>
</section>'''

ORDER = ["cover", "thesis", "why", "data", "sec-method", "detect", "control",
         "code-match", "validate", "sec-result", "r1", "r2", "regression",
         "takeaway", "honest", "bugs", "code-test", "repro"]

for sid in ORDER:
    (ROOT / "project" / "slides" / f"{sid}.html").write_text(S[sid], encoding="utf-8")

deck = {
    "v": 4,
    "createdOnFiles": {"v": 1, "at": "2026-09-19T09:30:00Z"},
    "title": "變換車道的外部成本",
    "order": ORDER,
    "cover": "cover",
    "sections": {
        "intro": {"description": "問題、資料與這份分析要回答什麼",
                  "start": "cover"},
        "method": {"description": "從軌跡到一個站得住的數字：偵測、對照組與驗證",
                   "start": "sec-method"},
        "result": {"description": "結果、核心結論與誠實的限制",
                   "start": "sec-result"},
    },
    "faces": {
        "noto-sans-tc": {
            "family": "Noto Sans TC",
            "href": "https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap",
        },
        "jetbrains-mono": {
            "family": "JetBrains Mono",
            "href": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap",
        },
    },
    "designSystems": [],
}
(ROOT / "project" / "deck.json").write_text(
    json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"wrote {len(ORDER)} slides + deck.json to {ROOT}")
