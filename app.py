import io
import math
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Flow Academy Daily Gold Terminal V4", page_icon="🟡", layout="wide")
APP_VERSION = "Flow Academy Daily Gold Terminal V4.0"
CACHE_TTL = 60 * 30

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'Cairo',sans-serif;}
.stApp {background:#070b12;color:#f7f7f7;}
[data-testid="stSidebar"] {background:#0b111c;}
.block-container {padding-top:2rem;}
.hero {background:linear-gradient(135deg,#0f1728,#111d31);border:1px solid #263756;border-radius:22px;padding:24px;}
.card {background:#111a2c;border:1px solid #273756;border-radius:18px;padding:18px;min-height:132px;}
.title {color:#9bb4d6;font-size:14px;margin-bottom:8px;}
.value {font-size:30px;font-weight:800;color:#ffd84d;}
.good {color:#18c77e;font-weight:800;}
.bad {color:#ff4b4b;font-weight:800;}
.neutral {color:#ffd84d;font-weight:800;}
.note {color:#8da0bd;font-size:13px;}
.report {background:#0f1728;border:1px solid #253759;border-radius:18px;padding:20px;white-space:pre-wrap;line-height:1.9;direction:rtl;text-align:right;}
.badge {border-radius:14px;padding:4px 10px;font-size:13px;background:#0c2743;color:#9ed0ff;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ---------------- Helpers ----------------
def safe_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, str):
            x = x.replace(',', '').replace('%', '').strip()
            if x in ['', '.', 'nan', 'None']:
                return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None

def fmt_num(x, digits=2):
    v = safe_float(x)
    return "No data" if v is None else f"{v:,.{digits}f}"

def fmt_int(x):
    v = safe_float(x)
    return "No data" if v is None else f"{int(round(v)):,.0f}"

def bias_ar(b):
    return {"bullish":"صاعد للذهب","bearish":"هابط للذهب","neutral":"محايد","nodata":"لا توجد بيانات"}.get(b,"محايد")

def cls(b):
    return "good" if b == "bullish" else "bad" if b == "bearish" else "neutral"

def weighted_score(items):
    total = 0
    valid_weight = 0
    for it in items:
        if not it.get("valid"):
            continue
        valid_weight += it["weight"]
        total += it["score"] * it["weight"]
    if valid_weight == 0:
        return 50, 0
    return round(total / valid_weight), round(valid_weight)

def card(title, value, bias, sub=""):
    st.markdown(f"""
    <div class="card">
      <div class="title">{title}</div>
      <div class="value">{value}</div>
      <div class="{cls(bias)}">{bias_ar(bias)}</div>
      <div class="note">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------------- Data ----------------
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fred(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"].replace('.', np.nan), errors="coerce")
    return df.dropna().tail(360)

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def yf_hist(ticker, period="6mo"):
    df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    df["Date"] = pd.to_datetime(df["Date"])
    return df

@st.cache_data(ttl=60*60*6, show_spinner=False)
def cot_gold_legacy():
    # Legacy Futures Only report. This is the layout that contains Non-Commercial Long/Short.
    url = "https://www.cftc.gov/dea/futures/deacmxlf.txt"
    try:
        text = requests.get(url, timeout=25).text
        m = re.search(r"GOLD\s+-\s+COMMODITY EXCHANGE INC\..*?(?=\n\s*[A-Z][A-Z\s/\-]+\s+-\s|\Z)", text, re.S)
        if not m:
            raise ValueError("Gold block not found")
        block = m.group(0)
        dm = re.search(r"AS OF\s+(\d{2}/\d{2}/\d{2})", block)
        as_of = dm.group(1) if dm else "No date"
        lines = block.splitlines()
        idx = None
        for i, ln in enumerate(lines):
            if "COMMITMENTS" in ln:
                idx = i
                break
        if idx is None:
            raise ValueError("Commitments line not found")
        numeric_lines = []
        for ln in lines[idx+1:]:
            nums = re.findall(r"-?\d{1,3}(?:,\d{3})*|-?\d+", ln)
            if len(nums) >= 9:
                numeric_lines.append(nums)
            if len(numeric_lines) >= 2:
                break
        if not numeric_lines:
            raise ValueError("Commitment numbers not found")
        nums = [int(n.replace(',', '')) for n in numeric_lines[0]]
        changes = [int(n.replace(',', '')) for n in numeric_lines[1]] if len(numeric_lines) > 1 else []
        long, short = nums[0], nums[1]
        net = long - short
        chg = changes[0] - changes[1] if len(changes) >= 2 else None
        if net > 100000:
            score, bias = 80, "bullish"
        elif net > 30000:
            score, bias = 65, "bullish"
        elif net > -30000:
            score, bias = 50, "neutral"
        else:
            score, bias = 30, "bearish"
        if chg is not None and chg < -10000:
            score -= 8
        if chg is not None and chg > 10000:
            score += 5
        return {"valid": True, "source":"CFTC Legacy Futures Only", "date":as_of, "long":long, "short":short, "net":net, "change":chg, "score":max(0,min(100,score)), "bias":bias}
    except Exception as e:
        return {"valid": False, "source":"CFTC Legacy Futures Only", "bias":"nodata", "score":50, "error":str(e)}

def yf_signal(ticker, title, inverse=False, threshold=0.0, period="6mo"):
    try:
        df = yf_hist(ticker, period)
        if df.empty or "Close" not in df:
            raise ValueError("No data")
        last = safe_float(df["Close"].iloc[-1])
        p1 = safe_float(df["Close"].iloc[-2]) if len(df) > 2 else None
        p5 = safe_float(df["Close"].iloc[-6]) if len(df) > 6 else None
        p20 = safe_float(df["Close"].iloc[-21]) if len(df) > 21 else None
        ch1 = None if p1 in [None, 0] else (last/p1 - 1) * 100
        ch5 = None if p5 in [None, 0] else (last/p5 - 1) * 100
        ch20 = None if p20 in [None, 0] else (last/p20 - 1) * 100
        ref = ch5 if ch5 is not None else ch20
        if ref is None or abs(ref) < threshold:
            bias, score = "neutral", 50
        else:
            rising = ref > threshold
            if inverse:
                bias, score = ("bearish", 25) if rising else ("bullish", 75)
            else:
                bias, score = ("bullish", 75) if rising else ("bearish", 25)
        return {"valid":True,"source":f"Yahoo Finance {ticker}","title":title,"date":df["Date"].iloc[-1],"value":last,"ch1":ch1,"ch5":ch5,"ch20":ch20,"bias":bias,"score":score,"df":df}
    except Exception as e:
        return {"valid":False,"source":f"Yahoo Finance {ticker}","title":title,"bias":"nodata","score":50,"error":str(e)}

def real_yield_signal():
    try:
        df = fred("DFII10")
        last = safe_float(df["value"].iloc[-1])
        p5 = safe_float(df["value"].iloc[-6]) if len(df) > 6 else None
        p20 = safe_float(df["value"].iloc[-21]) if len(df) > 21 else None
        ch5 = None if p5 is None else last - p5
        ch20 = None if p20 is None else last - p20
        ref = ch5 if ch5 is not None else ch20
        if ref is None or abs(ref) < 0.04:
            bias, score = "neutral", 50
        elif ref < 0:
            bias, score = "bullish", 75
        else:
            bias, score = "bearish", 25
        return {"valid":True,"source":"FRED DFII10","date":df["date"].iloc[-1],"value":last,"ch5":ch5,"ch20":ch20,"bias":bias,"score":score,"df":df}
    except Exception as e:
        return {"valid":False,"source":"FRED DFII10","bias":"nodata","score":50,"error":str(e)}

def us10y_signal():
    try:
        df = fred("DGS10")
        last = safe_float(df["value"].iloc[-1])
        p5 = safe_float(df["value"].iloc[-6]) if len(df) > 6 else None
        ch5 = None if p5 is None else last - p5
        if ch5 is None or abs(ch5) < 0.04:
            bias, score = "neutral", 50
        elif ch5 < 0:
            bias, score = "bullish", 70
        else:
            bias, score = "bearish", 30
        return {"valid":True,"source":"FRED DGS10","date":df["date"].iloc[-1],"value":last,"ch5":ch5,"bias":bias,"score":score,"df":df}
    except Exception as e:
        return {"valid":False,"source":"FRED DGS10","bias":"nodata","score":50,"error":str(e)}

def gold_silver_signal():
    g = yf_hist("GC=F", "6mo")
    s = yf_hist("SI=F", "6mo")
    if g.empty or s.empty:
        return {"valid":False,"source":"Yahoo Finance GC=F/SI=F","bias":"nodata","score":50}
    df = pd.merge(g[["Date","Close"]], s[["Date","Close"]], on="Date", suffixes=("_g","_s"))
    df["ratio"] = df["Close_g"] / df["Close_s"]
    last = safe_float(df["ratio"].iloc[-1])
    p5 = safe_float(df["ratio"].iloc[-6]) if len(df) > 6 else None
    ch5 = None if p5 in [None,0] else (last/p5 - 1) * 100
    if ch5 is None or abs(ch5) < 0.8:
        bias, score = "neutral", 50
    elif ch5 > 0:
        bias, score = "bullish", 65
    else:
        bias, score = "bearish", 35
return {"valid":True,"source":"Yahoo Finance XAUUSD/XAGUSD","date":df["Date"].iloc[-1],"value":last,"ch5":ch5,"bias":bias,"score":score,"df":df}
def line_chart(df, x, y, title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines", name=title))
    fig.update_layout(title=title, height=310, margin=dict(l=20,r=20,t=45,b=20), paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)

# ---------------- Sidebar ----------------
st.sidebar.markdown("### Flow Academy")
logo_path = Path("logo.png")
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)
else:
    st.sidebar.info("ارفع الشعار باسم logo.png داخل GitHub")
if st.sidebar.button("تحديث البيانات"):
    st.cache_data.clear(); st.rerun()
st.sidebar.markdown("---")
st.sidebar.markdown(APP_VERSION)
st.sidebar.markdown("Daily Score يعتمد على البيانات اليومية. COT يبقى فلتر أسبوعي فقط.")

# ---------------- Load ----------------
with st.spinner("جاري تحديث البيانات اليومية..."):
    gold = yf_signal("XAUUSD=X", "Spot Gold XAUUSD", False, 0.4)
    dxy = yf_signal("DX-Y.NYB", "DXY", True, 0.25)
    real = real_yield_signal()
    us10y = us10y_signal()
    vix = yf_signal("^VIX", "VIX", False, 3.0)
    hui = yf_signal("^HUI", "HUI Index", False, 0.7)
    ratio = gold_silver_signal()
    gld = yf_signal("GLD", "GLD Price Proxy", False, 0.5)
    cot = cot_gold_legacy()

# Daily scoring only
items_daily = [
    {"name":"DXY", "valid":dxy.get("valid"), "score":dxy.get("score",50), "weight":25},
    {"name":"Real Yield", "valid":real.get("valid"), "score":real.get("score",50), "weight":25},
    {"name":"VIX", "valid":vix.get("valid"), "score":vix.get("score",50), "weight":15},
    {"name":"Gold/Silver", "valid":ratio.get("valid"), "score":ratio.get("score",50), "weight":15},
    {"name":"HUI", "valid":hui.get("valid"), "score":hui.get("score",50), "weight":10},
    {"name":"Gold Momentum", "valid":gold.get("valid"), "score":gold.get("score",50), "weight":10},
]
daily_score, daily_reliability = weighted_score(items_daily)
weekly_score, weekly_reliability = weighted_score([
    {"name":"COT", "valid":cot.get("valid"), "score":cot.get("score",50), "weight":70},
    {"name":"GLD Proxy", "valid":gld.get("valid"), "score":gld.get("score",50), "weight":30},
])

if daily_score >= 70:
    daily_bias_ar, daily_bias_en = "السياق اليومي صاعد للذهب", "Bullish Daily Gold Context"
elif daily_score >= 55:
    daily_bias_ar, daily_bias_en = "السياق اليومي يميل للصعود", "Mild Bullish Daily Gold Context"
elif daily_score > 45:
    daily_bias_ar, daily_bias_en = "السياق اليومي محايد", "Neutral Daily Gold Context"
elif daily_score > 30:
    daily_bias_ar, daily_bias_en = "السياق اليومي يميل للهبوط", "Mild Bearish Daily Gold Context"
else:
    daily_bias_ar, daily_bias_en = "السياق اليومي هابط للذهب", "Bearish Daily Gold Context"

if weekly_score >= 60:
    weekly_bias = "صاعد"
elif weekly_score <= 40:
    weekly_bias = "هابط"
else:
    weekly_bias = "محايد"

# Intraday bias from 1D moves, not live intraday
valid_intraday = [dxy, real, gold, vix]
intra_raw = np.mean([x.get("score",50) for x in valid_intraday if x.get("valid")]) if any(x.get("valid") for x in valid_intraday) else 50
intraday_bias = "صاعد" if intra_raw >= 58 else "هابط" if intra_raw <= 42 else "محايد"

# ---------------- Header ----------------
left, right = st.columns([1,4])
with left:
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
with right:
    st.markdown(f"""
    <div class="hero">
      <h1>Flow Academy Daily Gold Terminal</h1>
      <h3>لوحة الذهب اليومية</h3>
      <p>COT, Real Yield, US10Y, DXY, VIX, HUI, Gold/Silver, GLD</p>
      <span class="badge">آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("### Daily Context Score")
c1,c2,c3,c4 = st.columns(4)
with c1: card("Daily Score", f"{daily_score}/100", "bullish" if daily_score>=55 else "bearish" if daily_score<=45 else "neutral", f"Reliability: {daily_reliability}%")
with c2: card("Gold Futures", fmt_num(gold.get('value')), gold.get('bias','nodata'), f"1D: {fmt_num(gold.get('ch1'))}% | 5D: {fmt_num(gold.get('ch5'))}%")
with c3: card("Real Yield 10Y", f"{fmt_num(real.get('value'))}%", real.get('bias','nodata'), f"5D: {fmt_num(real.get('ch5'))}")
with c4: card("DXY", fmt_num(dxy.get('value')), dxy.get('bias','nodata'), f"5D: {fmt_num(dxy.get('ch5'))}%")

st.markdown("### Flow Academy Bias")
b1,b2,b3 = st.columns(3)
with b1: card("Weekly Bias", weekly_bias, "bullish" if weekly_bias=="صاعد" else "bearish" if weekly_bias=="هابط" else "neutral", f"Weekly Reliability: {weekly_reliability}%")
with b2: card("Daily Bias", daily_bias_ar, "bullish" if daily_score>=55 else "bearish" if daily_score<=45 else "neutral", daily_bias_en)
with b3: card("Intraday Bias", intraday_bias, "bullish" if intraday_bias=="صاعد" else "bearish" if intraday_bias=="هابط" else "neutral", "من حركة اليوم وآخر 5 أيام")

st.markdown("### قراءة الأدوات اليومية")
r1,r2,r3,r4 = st.columns(4)
with r1: card("US10Y", f"{fmt_num(us10y.get('value'))}%", us10y.get('bias','nodata'), f"5D: {fmt_num(us10y.get('ch5'))}")
with r2: card("VIX", fmt_num(vix.get('value')), vix.get('bias','nodata'), f"5D: {fmt_num(vix.get('ch5'))}%")
with r3: card("HUI Index", fmt_num(hui.get('value')), hui.get('bias','nodata'), f"5D: {fmt_num(hui.get('ch5'))}%")
with r4: card("Gold/Silver", fmt_num(ratio.get('value')), ratio.get('bias','nodata'), f"5D: {fmt_num(ratio.get('ch5'))}%")

st.markdown("### Weekly Institutional Filter")
w1,w2,w3 = st.columns(3)
with w1: card("COT الصناديق", fmt_int(cot.get('net')), cot.get('bias','nodata'), f"Long: {fmt_int(cot.get('long'))} | Short: {fmt_int(cot.get('short'))} | As of: {cot.get('date','No date')}")
with w2: card("GLD Price Proxy", fmt_num(gld.get('value')), gld.get('bias','nodata'), f"5D: {fmt_num(gld.get('ch5'))}%")
with w3: card("Weekly Filter Score", f"{weekly_score}/100", "bullish" if weekly_score>=55 else "bearish" if weekly_score<=45 else "neutral", "COT أسبوعي، GLD يومي Proxy")

st.markdown("### النتيجة النهائية")
st.progress(daily_score/100)
st.markdown(f"## {daily_bias_ar}")
st.caption(daily_bias_en)

narrative = f"""
النظرة اليومية للذهب

النتيجة اليومية: {daily_score}/100
درجة موثوقية البيانات اليومية: {daily_reliability}%
السياق الحالي: {daily_bias_ar}

العوامل اليومية:
DXY: {bias_ar(dxy.get('bias','nodata'))}، القراءة الحالية {fmt_num(dxy.get('value'))}، تغير 5 أيام {fmt_num(dxy.get('ch5'))}%.
Real Yield 10Y: {bias_ar(real.get('bias','nodata'))}، القراءة الحالية {fmt_num(real.get('value'))}%، تغير 5 أيام {fmt_num(real.get('ch5'))}.
US10Y: {bias_ar(us10y.get('bias','nodata'))}، القراءة الحالية {fmt_num(us10y.get('value'))}%.
VIX: {bias_ar(vix.get('bias','nodata'))}، القراءة الحالية {fmt_num(vix.get('value'))}.
Gold/Silver Ratio: {bias_ar(ratio.get('bias','nodata'))}، القراءة الحالية {fmt_num(ratio.get('value'))}.
HUI Index: {bias_ar(hui.get('bias','nodata'))}، القراءة الحالية {fmt_num(hui.get('value'))}.

الفلتر الأسبوعي:
COT: {bias_ar(cot.get('bias','nodata'))}، صافي مراكز الصناديق {fmt_int(cot.get('net'))}، آخر تحديث {cot.get('date','No date')}.
GLD Proxy: {bias_ar(gld.get('bias','nodata'))}، القراءة الحالية {fmt_num(gld.get('value'))}.

قراءة أكاديمية فلو:
Weekly Bias: {weekly_bias}
Daily Bias: {daily_bias_ar}
Intraday Bias: {intraday_bias}

هذه القراءة تقيس الكونتكس العام قبل فتح الشارت. الدخول يبقى من TradingView بعد ظهور شروطك الفنية مثل MSS و FVG و ERL.
"""
st.markdown("### التقرير العربي")
st.markdown(f"<div class='report'>{narrative}</div>", unsafe_allow_html=True)
st.download_button("تحميل التقرير اليومي", narrative, file_name="flow_academy_daily_gold_report.txt")

st.markdown("### جودة البيانات")
quality = pd.DataFrame([
    ["Gold", gold.get('source'), gold.get('date','No date'), "نعم" if gold.get('valid') else "لا"],
    ["DXY", dxy.get('source'), dxy.get('date','No date'), "نعم" if dxy.get('valid') else "لا"],
    ["Real Yield", real.get('source'), real.get('date','No date'), "نعم" if real.get('valid') else "لا"],
    ["US10Y", us10y.get('source'), us10y.get('date','No date'), "نعم" if us10y.get('valid') else "لا"],
    ["VIX", vix.get('source'), vix.get('date','No date'), "نعم" if vix.get('valid') else "لا"],
    ["HUI", hui.get('source'), hui.get('date','No date'), "نعم" if hui.get('valid') else "لا"],
    ["Gold/Silver", ratio.get('source'), ratio.get('date','No date'), "نعم" if ratio.get('valid') else "لا"],
    ["GLD Proxy", gld.get('source'), gld.get('date','No date'), "نعم" if gld.get('valid') else "لا"],
    ["COT", cot.get('source'), cot.get('date','No date'), "نعم" if cot.get('valid') else "لا"],
], columns=["الأداة","المصدر","آخر تاريخ","يدخل بالنتيجة"])
st.dataframe(quality, use_container_width=True, hide_index=True)

st.markdown("### الرسوم")
g1,g2 = st.columns(2)
with g1:
    if real.get('valid'): line_chart(real['df'], 'date', 'value', 'Real Yield 10Y - FRED')
    if dxy.get('valid'): line_chart(dxy['df'], 'Date', 'Close', 'DXY')
with g2:
    if gold.get('valid'): line_chart(gold['df'], 'Date', 'Close', 'Gold Futures')
    if ratio.get('valid'): line_chart(ratio['df'], 'Date', 'ratio', 'Gold/Silver Ratio')

st.markdown(f"<div class='note'>{APP_VERSION} | البيانات اليومية هي الأساس، COT و ETF Filters تستخدم كفلتر أسبوعي فقط.</div>", unsafe_allow_html=True)
