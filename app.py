import io
import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(
    page_title="Flow Academy | Gold Institutional Dashboard",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "Flow Academy Gold Pro v2.0"

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {font-family: 'Cairo', sans-serif;}
    .stApp {background: #070B12; color: #F5F7FA;}
    section[data-testid="stSidebar"] {background: #0B111C; border-left: 1px solid #1f2937;}
    .main .block-container {padding-top: 1.5rem;}
    h1, h2, h3 {color: #F8D36B; font-weight: 800;}
    .brand-card {
        background: linear-gradient(135deg, #101827 0%, #111827 50%, #1F2937 100%);
        border: 1px solid #2D3748;
        border-radius: 22px;
        padding: 22px 26px;
        margin-bottom: 18px;
        box-shadow: 0 12px 35px rgba(0,0,0,0.25);
    }
    .brand-title {font-size: 36px; color: #F8D36B; font-weight: 800; margin: 0;}
    .brand-subtitle {font-size: 16px; color: #CBD5E1; margin-top: 8px;}
    .metric-card {
        background: #0F172A;
        border: 1px solid #273449;
        border-radius: 18px;
        padding: 18px;
        min-height: 150px;
    }
    .metric-title {font-size: 14px; color: #94A3B8; margin-bottom: 8px;}
    .metric-value {font-size: 25px; font-weight: 800; color: #F8FAFC; margin-bottom: 10px;}
    .badge-green {background:#123B2A; color:#4ADE80; padding:6px 10px; border-radius:999px; font-weight:700; font-size:13px;}
    .badge-red {background:#3B1518; color:#F87171; padding:6px 10px; border-radius:999px; font-weight:700; font-size:13px;}
    .badge-gray {background:#263244; color:#CBD5E1; padding:6px 10px; border-radius:999px; font-weight:700; font-size:13px;}
    .report-box {
        background:#0F172A;
        border:1px solid #273449;
        border-radius:18px;
        padding:20px;
        color:#E5E7EB;
        line-height:2;
        direction:rtl;
        text-align:right;
        white-space:pre-wrap;
    }
    .small-note {color:#94A3B8; font-size:13px;}
    div[data-testid="stMetricValue"] {color:#F8D36B;}
    div[data-testid="stMetricLabel"] {color:#CBD5E1;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- Helpers -----------------------------
@st.cache_data(ttl=60 * 30, show_spinner=False)
def fred_csv(series_id: str, years: int = 3) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url)
    df.columns = ["Date", "Value"]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"].replace(".", np.nan), errors="coerce")
    cutoff = pd.Timestamp.today() - pd.DateOffset(years=years)
    return df.dropna().query("Date >= @cutoff").reset_index(drop=True)

@st.cache_data(ttl=60 * 20, show_spinner=False)
def yf_hist(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False, threads=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    if "Date" not in df.columns:
        df.rename(columns={df.columns[0]: "Date"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df.dropna(subset=["Date"]).reset_index(drop=True)

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def cot_gold_current() -> dict:
    url = "https://www.cftc.gov/dea/futures/deacmxlf.htm"
    txt = requests.get(url, timeout=25).text
    # Gold block in legacy futures only, COMEX
    m = re.search(r"GOLD - COMMODITY EXCHANGE INC\..*?(?=\n[A-Z0-9 /&.'-]+ - [A-Z0-9 /&.'-]+\.|\Z)", txt, flags=re.S)
    if not m:
        return {"ok": False, "error": "COT gold block not found"}
    block = m.group(0)
    date_m = re.search(r"POSITIONS AS OF\s+([0-9/]+)", block)
    oi_m = re.search(r"OPEN INTEREST:\s+([0-9,]+)", block)
    nums_lines = re.findall(r"\n\s*([0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+\s+[0-9,]+)", block)
    if len(nums_lines) < 2:
        return {"ok": False, "error": "COT numeric lines not parsed"}
    commitments = [int(x.replace(",", "")) for x in nums_lines[0].split()]
    changes = [int(x.replace(",", "")) for x in nums_lines[1].split()]
    nc_long, nc_short, nc_spreads = commitments[0], commitments[1], commitments[2]
    ch_long, ch_short = changes[0], changes[1]
    net = nc_long - nc_short
    net_change = ch_long - ch_short
    return {
        "ok": True,
        "date": date_m.group(1) if date_m else "",
        "open_interest": int(oi_m.group(1).replace(",", "")) if oi_m else None,
        "nc_long": nc_long,
        "nc_short": nc_short,
        "nc_spreads": nc_spreads,
        "net": net,
        "net_change": net_change,
        "commercial_long": commitments[3],
        "commercial_short": commitments[4],
        "source": url,
    }


def last_close(df: pd.DataFrame):
    if df is None or df.empty or "Close" not in df.columns:
        return None
    return float(df["Close"].dropna().iloc[-1])


def pct_change(df: pd.DataFrame, days: int = 20):
    if df is None or df.empty or "Close" not in df.columns or len(df.dropna()) <= days:
        return None
    s = df["Close"].dropna()
    return float((s.iloc[-1] / s.iloc[-days] - 1) * 100)


def trend(df: pd.DataFrame, fast: int = 20, slow: int = 60):
    if df is None or df.empty or "Close" not in df.columns or len(df.dropna()) < slow:
        return "neutral"
    s = df["Close"].dropna()
    ma_fast = s.rolling(fast).mean().iloc[-1]
    ma_slow = s.rolling(slow).mean().iloc[-1]
    if ma_fast > ma_slow:
        return "up"
    if ma_fast < ma_slow:
        return "down"
    return "neutral"


def bias_ar(bias: str) -> str:
    return {"bullish": "صاعد للذهب", "bearish": "هابط للذهب", "neutral": "محايد", "nodata": "لا توجد بيانات"}.get(bias, "محايد")


def badge_class(bias: str) -> str:
    return "badge-green" if bias == "bullish" else "badge-red" if bias == "bearish" else "badge-gray"


def score_bias(bias: str, weight: int):
    if bias == "bullish":
        return weight
    if bias == "bearish":
        return -weight
    return 0


def render_card(title, value, detail, bias):
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-title">{title}</div>
          <div class="metric-value">{value}</div>
          <span class="{badge_class(bias)}">{detail}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def plot_line(df: pd.DataFrame, title: str, y_col: str = "Close"):
    if df is None or df.empty or y_col not in df.columns:
        st.info(f"لا توجد بيانات كافية لرسم {title}")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df[y_col], mode="lines", name=title))
    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=330,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="#070B12",
        plot_bgcolor="#0F172A",
        font=dict(color="#E5E7EB"),
    )
    st.plotly_chart(fig, use_container_width=True)

# ----------------------------- Sidebar -----------------------------
st.sidebar.markdown("### إعدادات أكاديمية فلو")
logo_file = st.sidebar.file_uploader("ارفع شعار الأكاديمية", type=["png", "jpg", "jpeg"])
if logo_file:
    st.sidebar.image(logo_file, use_container_width=True)
else:
    st.sidebar.markdown("ضع ملف الشعار باسم `logo.png` داخل GitHub حتى يظهر دائماً.")

refresh = st.sidebar.button("تحديث البيانات")
if refresh:
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(APP_VERSION)

# ----------------------------- Data -----------------------------
with st.spinner("جاري تحديث بيانات الذهب المؤسساتية..."):
    cot = cot_gold_current()
    real_df = fred_csv("DFII10", years=3)
    dxy_df = yf_hist("DX-Y.NYB", period="1y")
    hui_df = yf_hist("^HUI", period="1y")
    gld_df = yf_hist("GLD", period="1y")
    gold_df = yf_hist("GC=F", period="1y")
    silver_df = yf_hist("SI=F", period="1y")
    vix_df = yf_hist("^VIX", period="1y")

# Ratio
ratio_df = pd.DataFrame()
if not gold_df.empty and not silver_df.empty:
    g = gold_df[["Date", "Close"]].rename(columns={"Close": "Gold"})
    s = silver_df[["Date", "Close"]].rename(columns={"Close": "Silver"})
    ratio_df = pd.merge(g, s, on="Date", how="inner")
    ratio_df["Close"] = ratio_df["Gold"] / ratio_df["Silver"]

# Bias logic
cot_bias = "nodata"
if cot.get("ok"):
    if cot["net"] > 100000 and cot["net_change"] > -15000:
        cot_bias = "bullish"
    elif cot["net_change"] < -25000 or cot["net"] < 50000:
        cot_bias = "bearish"
    else:
        cot_bias = "neutral"

real_last = float(real_df["Value"].iloc[-1]) if not real_df.empty else None
real_chg_20 = float(real_df["Value"].iloc[-1] - real_df["Value"].iloc[-20]) if len(real_df) > 20 else None
real_bias = "nodata" if real_chg_20 is None else "bullish" if real_chg_20 < -0.05 else "bearish" if real_chg_20 > 0.05 else "neutral"

dxy_t = trend(dxy_df)
dxy_bias = "bullish" if dxy_t == "down" else "bearish" if dxy_t == "up" else "neutral"

hui_t = trend(hui_df)
hui_bias = "bullish" if hui_t == "up" else "bearish" if hui_t == "down" else "neutral"

ratio_t = trend(ratio_df)
ratio_bias = "bullish" if ratio_t == "up" else "neutral" if ratio_t == "down" else "neutral"

gld_t = trend(gld_df)
gld_vol = pct_change(gld_df, 20)
gld_bias = "bullish" if gld_t == "up" else "bearish" if gld_t == "down" else "neutral"

vix_t = trend(vix_df)
vix_bias = "bullish" if vix_t == "up" else "neutral"

# Score 100
score = 50
score += score_bias(cot_bias, 18)
score += score_bias(real_bias, 18)
score += score_bias(dxy_bias, 14)
score += score_bias(hui_bias, 14)
score += score_bias(gld_bias, 14)
score += score_bias(ratio_bias, 8)
score += score_bias(vix_bias, 4)
score = max(0, min(100, score))

if score >= 70:
    final_label = "Strong Bullish Gold Context"
    final_ar = "السياق المؤسساتي صاعد للذهب"
elif score >= 58:
    final_label = "Bullish Gold Context"
    final_ar = "السياق يميل لصالح الذهب"
elif score <= 30:
    final_label = "Strong Bearish Gold Context"
    final_ar = "السياق المؤسساتي هابط للذهب"
elif score <= 42:
    final_label = "Bearish Gold Context"
    final_ar = "السياق يضغط على الذهب"
else:
    final_label = "Neutral Gold Context"
    final_ar = "السياق محايد"

# ----------------------------- Header -----------------------------
header_cols = st.columns([1, 5])
with header_cols[0]:
    if logo_file:
        st.image(logo_file, use_container_width=True)
    else:
        st.markdown("<div style='font-size:52px;text-align:center;'>𓂀</div>", unsafe_allow_html=True)
with header_cols[1]:
    st.markdown(
        f"""
        <div class="brand-card">
          <p class="brand-title">أكاديمية فلو | لوحة الذهب المؤسساتية</p>
          <div class="brand-subtitle">COT, Real Yield, DXY, HUI, Gold/Silver Ratio, GLD, VIX</div>
          <div class="small-note">آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------- Top metrics -----------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Institutional Score", f"{score}/100", final_ar)
with col2:
    st.metric("Gold Futures", f"{last_close(gold_df):,.2f}" if last_close(gold_df) else "No data", f"{pct_change(gold_df, 20):.2f}% 20D" if pct_change(gold_df, 20) else "")
with col3:
    st.metric("Real Yield 10Y", f"{real_last:.2f}%" if real_last is not None else "No data", f"{real_chg_20:.2f} 20D" if real_chg_20 is not None else "")
with col4:
    st.metric("DXY", f"{last_close(dxy_df):.2f}" if last_close(dxy_df) else "No data", bias_ar(dxy_bias))

st.markdown("### قراءة الأدوات")
cols = st.columns(5)
with cols[0]:
    detail = f"Net {cot.get('net', 0):,}" if cot.get("ok") else "No data"
    render_card("COT الصناديق", bias_ar(cot_bias), detail, cot_bias)
with cols[1]:
    detail = f"{real_last:.2f}%" if real_last is not None else "No data"
    render_card("Real Yield 10Y", bias_ar(real_bias), detail, real_bias)
with cols[2]:
    detail = f"{last_close(hui_df):.2f}" if last_close(hui_df) else "No data"
    render_card("HUI Index", bias_ar(hui_bias), detail, hui_bias)
with cols[3]:
    detail = f"{last_close(ratio_df):.2f}" if last_close(ratio_df) else "No data"
    render_card("Gold/Silver", bias_ar(ratio_bias), detail, ratio_bias)
with cols[4]:
    detail = f"{last_close(gld_df):.2f}" if last_close(gld_df) else "No data"
    render_card("GLD Proxy", bias_ar(gld_bias), detail, gld_bias)

st.markdown("### النتيجة النهائية")
st.progress(score / 100)
st.markdown(f"## {final_ar}")
st.caption(final_label)

cot_date = cot.get("date", "No data") if cot.get("ok") else "No data"
net = cot.get("net", "No data") if cot.get("ok") else "No data"
net_change = cot.get("net_change", "No data") if cot.get("ok") else "No data"

def fmt(x, decimals=2):
    if x is None:
        return "No data"
    try:
        return f"{x:,.{decimals}f}"
    except Exception:
        return str(x)

report_ar = f"""
النظرة المؤسساتية على الذهب | أكاديمية فلو

النتيجة النهائية: {final_ar}
الدرجة المؤسساتية: {score}/100

COT الذهب: {bias_ar(cot_bias)}
تاريخ التقرير: {cot_date}
صافي مراكز الصناديق: {net:,} عقد
التغير الأسبوعي: {net_change:,} عقد

Real Yield 10Y: {bias_ar(real_bias)}
القراءة الحالية: {fmt(real_last)}%
تغير 20 يوم: {fmt(real_chg_20)}

DXY: {bias_ar(dxy_bias)}
القراءة الحالية: {fmt(last_close(dxy_df))}

HUI Index: {bias_ar(hui_bias)}
القراءة الحالية: {fmt(last_close(hui_df))}

Gold/Silver Ratio: {bias_ar(ratio_bias)}
القراءة الحالية: {fmt(last_close(ratio_df))}

GLD Proxy: {bias_ar(gld_bias)}
القراءة الحالية: {fmt(last_close(gld_df))}

القراءة العملية:
إذا توافق هذا السياق مع تحليل ICT وظهرت مناطق طلب واضحة، يصبح البحث عن فرص شراء أدق.
إذا ارتفع Real Yield وDXY مع ضعف HUI وGLD، تصبح أي صعودات على الذهب أضعف مؤسسياً.
هذا تحليل مؤسساتي وليس توصية تداول.
"""

report_en = f"""
Flow Academy Gold Institutional Outlook

Final Bias: {final_label}
Institutional Score: {score}/100

Gold COT: {bias_ar(cot_bias)}
Report Date: {cot_date}
Non-commercial Net Position: {net:,} contracts
Weekly Net Change: {net_change:,} contracts

Real Yield 10Y: {bias_ar(real_bias)}
Current Reading: {fmt(real_last)}%
20-Day Change: {fmt(real_chg_20)}

DXY: {bias_ar(dxy_bias)} | Current: {fmt(last_close(dxy_df))}
HUI Index: {bias_ar(hui_bias)} | Current: {fmt(last_close(hui_df))}
Gold/Silver Ratio: {bias_ar(ratio_bias)} | Current: {fmt(last_close(ratio_df))}
GLD Proxy: {bias_ar(gld_bias)} | Current: {fmt(last_close(gld_df))}

Practical reading:
When this institutional context aligns with ICT demand, bullish setups carry better confirmation.
When Real Yield and DXY rise while HUI and GLD weaken, gold rallies lose institutional support.
This is analysis, not financial advice.
"""

arabic_tab, english_tab, charts_tab, sources_tab = st.tabs(["التقرير العربي", "English Report", "الرسوم", "المصادر"])
with arabic_tab:
    st.markdown(f"<div class='report-box'>{report_ar}</div>", unsafe_allow_html=True)
    st.download_button("تحميل التقرير العربي", report_ar, file_name="flow_gold_report_ar.txt")
with english_tab:
    st.markdown(f"<div class='report-box' style='direction:ltr;text-align:left'>{report_en}</div>", unsafe_allow_html=True)
    st.download_button("Download English Report", report_en, file_name="flow_gold_report_en.txt")
with charts_tab:
    c1, c2 = st.columns(2)
    with c1:
        plot_line(real_df.rename(columns={"Value": "Close"}), "Real Yield 10Y")
        plot_line(dxy_df, "DXY")
        plot_line(gld_df, "GLD Proxy")
    with c2:
        plot_line(gold_df, "Gold Futures")
        plot_line(hui_df, "HUI Gold Bugs Index")
        plot_line(ratio_df, "Gold/Silver Ratio")
with sources_tab:
    st.markdown(
        """
        مصادر البيانات:
        - CFTC Legacy Futures Only COT
        - FRED DFII10 Real Yield 10Y
        - Yahoo Finance عبر yfinance: Gold Futures, Silver Futures, DXY, HUI, GLD, VIX

        ملاحظات:
        - COT يتحدث أسبوعياً.
        - Real Yield يتحدث حسب توفر بيانات FRED.
        - GLD هنا Proxy سعري وليس تدفقات ETF الرسمية.
        - لتفعيل الشعار دائماً، ارفع ملف logo.png داخل نفس مستودع GitHub.
        """
    )

