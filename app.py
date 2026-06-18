import io
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Flow Academy Gold Pro V3", page_icon="🟡", layout="wide")

APP_VERSION = "Flow Academy Gold Pro V3.0"
CACHE_TTL = 60 * 30

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {font-family: 'Cairo', sans-serif;}
.stApp {background:#070b12;color:#f7f7f7;}
[data-testid="stSidebar"] {background:#0b111c;}
.main-card {background:linear-gradient(135deg,#0f1728,#111d31);border:1px solid #233150;border-radius:22px;padding:22px;}
.metric-card {background:#111a2c;border:1px solid #273756;border-radius:18px;padding:18px;min-height:140px;}
.metric-title {color:#9bb4d6;font-size:14px;margin-bottom:10px;}
.metric-value {font-size:30px;font-weight:800;color:#ffd84d;}
.good {color:#19c37d;font-weight:800;}
.bad {color:#ff4b4b;font-weight:800;}
.neutral {color:#ffd84d;font-weight:800;}
.source-ok {background:#053b25;color:#22d884;border-radius:14px;padding:4px 10px;font-size:13px;}
.source-bad {background:#421515;color:#ff6868;border-radius:14px;padding:4px 10px;font-size:13px;}
.source-warn {background:#4a3b08;color:#ffd84d;border-radius:14px;padding:4px 10px;font-size:13px;}
.report-box {background:#0f1728;border:1px solid #253759;border-radius:18px;padding:20px;white-space:pre-wrap;line-height:1.9;direction:rtl;text-align:right;}
.small-note {color:#8da0bd;font-size:13px;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------- Helpers -----------------------------

def safe_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, str):
            x = x.replace(",", "").replace("%", "").strip()
            if x in ["", ".", "nan", "None"]:
                return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def fmt_num(x, digits=2):
    v = safe_float(x)
    if v is None:
        return "No data"
    return f"{v:,.{digits}f}"


def fmt_int(x):
    v = safe_float(x)
    if v is None:
        return "No data"
    return f"{int(round(v)):,.0f}"


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def age_status(date_value):
    if date_value is None or pd.isna(date_value):
        return "No date", "bad"
    try:
        d = pd.to_datetime(date_value).tz_localize(None)
        age = (pd.Timestamp.utcnow().tz_localize(None) - d).days
        if age <= 3:
            return f"حديث: {age} يوم", "ok"
        if age <= 10:
            return f"متأخر: {age} يوم", "warn"
        return f"قديم: {age} يوم", "bad"
    except Exception:
        return "No date", "bad"


def source_badge(label, status="ok"):
    cls = "source-ok" if status == "ok" else "source-warn" if status == "warn" else "source-bad"
    return f"<span class='{cls}'>{label}</span>"


def bias_ar(bias):
    return {
        "bullish": "صاعد للذهب",
        "bearish": "هابط للذهب",
        "neutral": "محايد",
        "nodata": "لا توجد بيانات",
    }.get(bias, "محايد")


def bias_class(bias):
    if bias == "bullish":
        return "good"
    if bias == "bearish":
        return "bad"
    return "neutral"


def weighted_score(items):
    valid_weight = 0
    total = 0
    for item in items:
        if not item.get("valid"):
            continue
        valid_weight += item["weight"]
        total += item["score"] * item["weight"]
    if valid_weight == 0:
        return None, 0
    score = round(total / valid_weight)
    reliability = round(valid_weight)
    return score, reliability


def metric_card(title, value, bias, sub="", source=""):
    cls = bias_class(bias)
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="{cls}">{bias_ar(bias)}</div>
            <div class="small-note">{sub}</div>
            <div style="margin-top:8px;">{source}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------- Data Sources -----------------------------

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_fred_series(series_id):
    # FRED CSV endpoint without API key
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"].replace(".", np.nan), errors="coerce")
    df = df.dropna().tail(260)
    return df

@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_yf_history(ticker, period="6mo"):
    data = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=False)
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [c[0] for c in data.columns]
    data = data.reset_index()
    data["Date"] = pd.to_datetime(data["Date"])
    return data

@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_cot_gold():
    # CFTC current legacy futures only, compressed CSV
    urls = [
        "https://www.cftc.gov/dea/newcot/f_disagg.txt",
        "https://www.cftc.gov/dea/newcot/deacmxlf.txt",
        "https://www.cftc.gov/dea/futures/deacmxlf.txt",
    ]
    last_error = None
    for url in urls:
        try:
            text = requests.get(url, timeout=25).text
            # Try fixed CFTC text report parser for gold block
            m = re.search(r"GOLD\s+-\s+COMMODITY EXCHANGE INC\..*?(?=\n\s*[A-Z][A-Z\s/\-]+-\s|\Z)", text, re.S)
            if not m:
                continue
            block = m.group(0)
            # Date
            dm = re.search(r"AS OF\s+(\d{2}/\d{2}/\d{2})", block)
            as_of = dm.group(1) if dm else "No date"
            # First commitment line after COMMITMENTS
            lines = [ln for ln in block.splitlines() if re.search(r"\d", ln)]
            commit_line = None
            change_line = None
            for i, ln in enumerate(lines):
                if "OPEN INTEREST" in ln:
                    continue
                nums = re.findall(r"-?\d{1,3}(?:,\d{3})*|-?\d+", ln)
                if len(nums) >= 9:
                    commit_line = ln
                    # next numeric line likely changes
                    for ln2 in lines[i+1:]:
                        nums2 = re.findall(r"-?\d{1,3}(?:,\d{3})*|-?\d+", ln2)
                        if len(nums2) >= 9:
                            change_line = ln2
                            break
                    break
            if not commit_line:
                continue
            nums = [int(n.replace(",", "")) for n in re.findall(r"-?\d{1,3}(?:,\d{3})*|-?\d+", commit_line)]
            chnums = [int(n.replace(",", "")) for n in re.findall(r"-?\d{1,3}(?:,\d{3})*|-?\d+", change_line or "")]
            # Layout from legacy: non-commercial long, short, spreads, commercial long, short...
            noncom_long, noncom_short = nums[0], nums[1]
            net = noncom_long - noncom_short
            change_net = None
            if len(chnums) >= 2:
                change_net = chnums[0] - chnums[1]
            bias = "bullish" if net > 0 else "bearish" if net < 0 else "neutral"
            # Score uses net and weekly change. Crowded long but still positive.
            score = 75 if net > 100000 else 60 if net > 30000 else 45 if net > 0 else 25
            if change_net is not None and change_net < -10000:
                score -= 10
            if change_net is not None and change_net > 10000:
                score += 5
            score = max(0, min(100, score))
            return {
                "valid": True, "source": "CFTC", "as_of": as_of, "long": noncom_long,
                "short": noncom_short, "net": net, "change_net": change_net,
                "bias": bias, "score": score, "raw_url": url
            }
        except Exception as e:
            last_error = str(e)
            continue
    return {"valid": False, "source": "CFTC", "bias": "nodata", "score": 50, "error": last_error}


def real_yield_signal():
    try:
        df = get_fred_series("DFII10")
        last = safe_float(df["value"].iloc[-1])
        prev20 = safe_float(df["value"].iloc[-21]) if len(df) > 21 else None
        change20 = None if prev20 is None or last is None else last - prev20
        # For gold: falling real yield bullish, rising bearish
        if change20 is None:
            bias = "neutral"; score = 50
        elif change20 < -0.10:
            bias = "bullish"; score = 75
        elif change20 > 0.10:
            bias = "bearish"; score = 25
        else:
            bias = "neutral"; score = 50
        return {"valid": True, "source": "FRED DFII10", "date": df["date"].iloc[-1], "value": last, "change20": change20, "bias": bias, "score": score, "df": df}
    except Exception as e:
        return {"valid": False, "source": "FRED DFII10", "bias": "nodata", "score": 50, "error": str(e)}


def yf_signal(ticker, title, gold_inverse=False, threshold=0.0, period="6mo"):
    try:
        df = get_yf_history(ticker, period)
        if df.empty or "Close" not in df:
            raise ValueError("No data")
        last = safe_float(df["Close"].iloc[-1])
        prev20 = safe_float(df["Close"].iloc[-21]) if len(df) > 21 else None
        change_pct = None if prev20 in [None, 0] or last is None else (last / prev20 - 1) * 100
        if change_pct is None:
            bias = "neutral"; score = 50
        else:
            rising = change_pct > threshold
            falling = change_pct < -threshold
            if gold_inverse:
                bias = "bearish" if rising else "bullish" if falling else "neutral"
                score = 25 if rising else 75 if falling else 50
            else:
                bias = "bullish" if rising else "bearish" if falling else "neutral"
                score = 75 if rising else 25 if falling else 50
        return {"valid": True, "source": f"Yahoo Finance {ticker}", "title": title, "date": df["Date"].iloc[-1], "value": last, "change20": change_pct, "bias": bias, "score": score, "df": df}
    except Exception as e:
        return {"valid": False, "source": f"Yahoo Finance {ticker}", "title": title, "bias": "nodata", "score": 50, "error": str(e)}


def gold_silver_signal():
    gold = yf_signal("GC=F", "Gold Futures", False, 0.0)
    silver = yf_signal("SI=F", "Silver Futures", False, 0.0)
    if not gold.get("valid") or not silver.get("valid"):
        return {"valid": False, "source": "Yahoo Finance GC=F/SI=F", "bias": "nodata", "score": 50}
    gdf, sdf = gold["df"].copy(), silver["df"].copy()
    df = pd.merge(gdf[["Date", "Close"]], sdf[["Date", "Close"]], on="Date", suffixes=("_gold", "_silver"))
    df["ratio"] = df["Close_gold"] / df["Close_silver"]
    last = safe_float(df["ratio"].iloc[-1])
    prev20 = safe_float(df["ratio"].iloc[-21]) if len(df) > 21 else None
    change20 = None if prev20 in [None, 0] else (last / prev20 - 1) * 100
    # Rising ratio means gold stronger than silver, defensive support for gold.
    if change20 is None:
        bias = "neutral"; score = 50
    elif change20 > 1.0:
        bias = "bullish"; score = 65
    elif change20 < -1.0:
        bias = "bearish"; score = 35
    else:
        bias = "neutral"; score = 50
    return {"valid": True, "source": "Yahoo Finance GC=F/SI=F", "date": df["Date"].iloc[-1], "value": last, "change20": change20, "bias": bias, "score": score, "df": df}


def gld_proxy_signal():
    # GLD price proxy. Official ETF flows need WGC file/API access. This proxy does NOT replace WGC holdings flows.
    return yf_signal("GLD", "GLD ETF Proxy", False, 1.0)

# ----------------------------- Sidebar -----------------------------

st.sidebar.markdown("### إعدادات أكاديمية فلو")
logo_path = Path("logo.png")
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)
else:
    st.sidebar.markdown("الشعار غير موجود. ارفع الملف باسم logo.png داخل GitHub.")

if st.sidebar.button("تحديث البيانات"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(APP_VERSION)
st.sidebar.markdown("مصادر رسمية قدر الإمكان. أي بيانات ناقصة لا تدخل في النتيجة.")

# ----------------------------- Load Data -----------------------------

with st.spinner("جاري سحب البيانات من المصادر..."):
    cot = get_cot_gold()
    real = real_yield_signal()
    gold = yf_signal("GC=F", "Gold Futures", False, 1.0)
    dxy = yf_signal("DX-Y.NYB", "DXY", True, 0.5)
    hui = yf_signal("^HUI", "HUI Index", False, 1.0)
    ratio = gold_silver_signal()
    gld = gld_proxy_signal()
    vix = yf_signal("^VIX", "VIX", False, 5.0)
    us10y = get_fred_series("DGS10") if True else pd.DataFrame()

items = [
    {"name":"COT", "valid":cot.get("valid", False), "score":cot.get("score",50), "weight":25},
    {"name":"Real Yield", "valid":real.get("valid", False), "score":real.get("score",50), "weight":25},
    {"name":"DXY", "valid":dxy.get("valid", False), "score":dxy.get("score",50), "weight":15},
    {"name":"GLD", "valid":gld.get("valid", False), "score":gld.get("score",50), "weight":15},
    {"name":"HUI", "valid":hui.get("valid", False), "score":hui.get("score",50), "weight":10},
    {"name":"Gold/Silver", "valid":ratio.get("valid", False), "score":ratio.get("score",50), "weight":5},
    {"name":"VIX", "valid":vix.get("valid", False), "score":vix.get("score",50), "weight":5},
]
score, reliability = weighted_score(items)
score = 0 if score is None else score

if score >= 70:
    final_ar = "السياق المؤسساتي صاعد للذهب"
    final_en = "Strong Bullish Gold Context"
elif score >= 55:
    final_ar = "السياق المؤسساتي يميل للصعود"
    final_en = "Bullish Gold Context"
elif score > 45:
    final_ar = "السياق المؤسساتي محايد"
    final_en = "Neutral Gold Context"
elif score > 30:
    final_ar = "السياق المؤسساتي يميل للهبوط"
    final_en = "Bearish Gold Context"
else:
    final_ar = "السياق المؤسساتي هابط للذهب"
    final_en = "Strong Bearish Gold Context"

# ----------------------------- Header -----------------------------

col_logo, col_head = st.columns([1, 4])
with col_logo:
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
with col_head:
    st.markdown(
        f"""
        <div class="main-card">
        <h1>Flow Academy Gold Intelligence</h1>
        <h3>لوحة الذهب المؤسساتية</h3>
        <p>COT, Real Yield, DXY, HUI, Gold/Silver Ratio, GLD, VIX</p>
        <p class="small-note">آخر تحديث: {now_text()}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# Top metrics
m1, m2, m3, m4 = st.columns(4)
with m1:
    metric_card("Institutional Score", f"{score}/100", "bullish" if score>=55 else "bearish" if score<=45 else "neutral", f"Reliability: {reliability}%")
with m2:
    metric_card("Gold Futures", fmt_num(gold.get("value"),2), gold.get("bias","nodata"), f"20D: {fmt_num(gold.get('change20'),2)}%")
with m3:
    metric_card("Real Yield 10Y", f"{fmt_num(real.get('value'),2)}%", real.get("bias","nodata"), f"20D: {fmt_num(real.get('change20'),2)}")
with m4:
    metric_card("DXY", fmt_num(dxy.get("value"),2), dxy.get("bias","nodata"), f"20D: {fmt_num(dxy.get('change20'),2)}%")

st.markdown("## قراءة الأدوات")
cols = st.columns(5)
with cols[0]:
    cot_sub = f"Net {fmt_int(cot.get('net'))} | Δ {fmt_int(cot.get('change_net'))}" if cot.get("valid") else cot.get("error", "No data")
    metric_card("COT الصناديق", fmt_int(cot.get("net")) if cot.get("valid") else "No data", cot.get("bias","nodata"), cot_sub, source_badge(cot.get("source","CFTC"), "ok" if cot.get("valid") else "bad"))
with cols[1]:
    metric_card("Real Yield 10Y", f"{fmt_num(real.get('value'),2)}%", real.get("bias","nodata"), f"20D: {fmt_num(real.get('change20'),2)}", source_badge(real.get("source","FRED"), "ok" if real.get("valid") else "bad"))
with cols[2]:
    metric_card("HUI Index", fmt_num(hui.get("value"),2), hui.get("bias","nodata"), f"20D: {fmt_num(hui.get('change20'),2)}%", source_badge(hui.get("source","Yahoo"), "ok" if hui.get("valid") else "bad"))
with cols[3]:
    metric_card("Gold/Silver", fmt_num(ratio.get("value"),2), ratio.get("bias","nodata"), f"20D: {fmt_num(ratio.get('change20'),2)}%", source_badge(ratio.get("source","Yahoo"), "ok" if ratio.get("valid") else "bad"))
with cols[4]:
    metric_card("GLD Proxy", fmt_num(gld.get("value"),2), gld.get("bias","nodata"), f"20D: {fmt_num(gld.get('change20'),2)}%", source_badge("Yahoo GLD proxy", "ok" if gld.get("valid") else "bad"))

st.markdown("## النتيجة النهائية")
st.progress(score / 100)
st.markdown(f"<h2>{final_ar}</h2><p>{final_en}</p>", unsafe_allow_html=True)

# Data quality table
st.markdown("## جودة البيانات")
quality_rows = []
for name, obj in [("COT", cot), ("Real Yield", real), ("Gold", gold), ("DXY", dxy), ("HUI", hui), ("Gold/Silver", ratio), ("GLD Proxy", gld), ("VIX", vix)]:
    valid = obj.get("valid", False)
    date = obj.get("date", obj.get("as_of", "No date"))
    quality_rows.append({
        "الأداة": name,
        "المصدر": obj.get("source", "No source"),
        "الحالة": "شغال" if valid else "فشل",
        "آخر تاريخ": str(date),
        "يدخل بالسكور": "نعم" if valid else "لا",
    })
st.dataframe(pd.DataFrame(quality_rows), use_container_width=True, hide_index=True)

# Reports
cot_net_text = fmt_int(cot.get("net")) if cot.get("valid") else "No data"
cot_change_text = fmt_int(cot.get("change_net")) if cot.get("valid") else "No data"
real_value_text = fmt_num(real.get("value"), 2)
dxy_value_text = fmt_num(dxy.get("value"), 2)
hui_value_text = fmt_num(hui.get("value"), 2)
ratio_value_text = fmt_num(ratio.get("value"), 2)
gld_value_text = fmt_num(gld.get("value"), 2)

report_ar = f"""
النظرة المؤسساتية على الذهب

النتيجة النهائية: {final_ar}
الدرجة المؤسساتية: {score}/100
موثوقية البيانات: {reliability}%

COT الصناديق:
القراءة: {bias_ar(cot.get('bias','nodata'))}
صافي مراكز الصناديق: {cot_net_text}
التغير الأسبوعي: {cot_change_text}
المصدر: {cot.get('source','CFTC')}

Real Yield 10Y:
القراءة: {bias_ar(real.get('bias','nodata'))}
القيمة الحالية: {real_value_text}%
تغير 20 يوم: {fmt_num(real.get('change20'), 2)}
المصدر: {real.get('source','FRED')}

DXY:
القراءة: {bias_ar(dxy.get('bias','nodata'))}
القيمة الحالية: {dxy_value_text}
تغير 20 يوم: {fmt_num(dxy.get('change20'), 2)}%

HUI Index:
القراءة: {bias_ar(hui.get('bias','nodata'))}
القيمة الحالية: {hui_value_text}

Gold/Silver Ratio:
القراءة: {bias_ar(ratio.get('bias','nodata'))}
القيمة الحالية: {ratio_value_text}

GLD Proxy:
القراءة: {bias_ar(gld.get('bias','nodata'))}
القيمة الحالية: {gld_value_text}

قراءة أكاديمية فلو:
إذا ارتفعت الدرجة فوق 70 فهذا يدعم استمرار الاتجاه الصاعد للذهب مؤسساتياً.
إذا هبطت الدرجة تحت 30 فهذا يعكس ضغطاً مؤسساتياً واضحاً على الذهب.
أي قراءة بين 45 و55 تعتبر محايدة وتحتاج تأكيداً من حركة السعر.
""".strip()

report_en = f"""
Flow Academy Gold Institutional Report

Final Context: {final_en}
Institutional Score: {score}/100
Data Reliability: {reliability}%

COT Funds: {bias_ar(cot.get('bias','nodata'))} | Net: {cot_net_text} | Weekly Change: {cot_change_text}
Real Yield 10Y: {bias_ar(real.get('bias','nodata'))} | Current: {real_value_text}%
DXY: {bias_ar(dxy.get('bias','nodata'))} | Current: {dxy_value_text}
HUI Index: {bias_ar(hui.get('bias','nodata'))} | Current: {hui_value_text}
Gold/Silver Ratio: {bias_ar(ratio.get('bias','nodata'))} | Current: {ratio_value_text}
GLD Proxy: {bias_ar(gld.get('bias','nodata'))} | Current: {gld_value_text}
""".strip()

st.markdown("## التقرير")
tab_ar, tab_en = st.tabs(["تقرير عربي", "English Report"])
with tab_ar:
    st.markdown(f"<div class='report-box'>{report_ar}</div>", unsafe_allow_html=True)
    st.download_button("تحميل التقرير العربي TXT", report_ar, file_name="flow_gold_report_ar.txt")
with tab_en:
    st.markdown(f"<div class='report-box' style='direction:ltr;text-align:left'>{report_en}</div>", unsafe_allow_html=True)
    st.download_button("Download English TXT", report_en, file_name="flow_gold_report_en.txt")

# Charts
st.markdown("## الرسوم")
chart_cols = st.columns(2)
with chart_cols[0]:
    if real.get("valid"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=real["df"]["date"], y=real["df"]["value"], mode="lines", name="Real Yield 10Y"))
        fig.update_layout(template="plotly_dark", height=360, margin=dict(l=20,r=20,t=40,b=20), title="Real Yield 10Y - FRED")
        st.plotly_chart(fig, use_container_width=True)
with chart_cols[1]:
    if gold.get("valid"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=gold["df"]["Date"], y=gold["df"]["Close"], mode="lines", name="Gold Futures"))
        fig.update_layout(template="plotly_dark", height=360, margin=dict(l=20,r=20,t=40,b=20), title="Gold Futures")
        st.plotly_chart(fig, use_container_width=True)

chart_cols2 = st.columns(2)
with chart_cols2[0]:
    if dxy.get("valid"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dxy["df"]["Date"], y=dxy["df"]["Close"], mode="lines", name="DXY"))
        fig.update_layout(template="plotly_dark", height=360, margin=dict(l=20,r=20,t=40,b=20), title="DXY")
        st.plotly_chart(fig, use_container_width=True)
with chart_cols2[1]:
    if ratio.get("valid"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ratio["df"]["Date"], y=ratio["df"]["ratio"], mode="lines", name="Gold/Silver Ratio"))
        fig.update_layout(template="plotly_dark", height=360, margin=dict(l=20,r=20,t=40,b=20), title="Gold/Silver Ratio")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("Flow Academy Gold Pro V3.0 | البيانات الناقصة لا تدخل في النتيجة النهائية.")
