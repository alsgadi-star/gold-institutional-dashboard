import math
import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Flow Academy Daily Gold Terminal V5.2",
    page_icon="🟡",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_VERSION = "Flow Academy Daily Gold Terminal V5.3 Pro Visual Identity"
CACHE_TTL = 60 * 30

hide_streamlit_style = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

:root{
    --fa-bg:#050a12;
    --fa-panel:#0b1220;
    --fa-card:#111a2b;
    --fa-card2:#0e1728;
    --fa-border:#233553;
    --fa-text:#f8fafc;
    --fa-muted:#94a3b8;
    --fa-gold:#f6c453;
    --fa-cyan:#17b7e8;
    --fa-green:#12d18e;
    --fa-red:#ff4d5a;
    --fa-amber:#f59e0b;
}

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}
[data-testid="stToolbar"] {display:none;}
[data-testid="stDecoration"] {display:none;}
[data-testid="stStatusWidget"] {display:none;}
[data-testid="collapsedControl"] {display:none;}

html, body, [data-testid="stAppViewContainer"]{
    background:
        radial-gradient(circle at 10% 0%, rgba(23,183,232,.16), transparent 28%),
        radial-gradient(circle at 90% 5%, rgba(246,196,83,.12), transparent 22%),
        linear-gradient(180deg, #050a12 0%, #07111e 55%, #050a12 100%);
    color:var(--fa-text);
    font-family:'Cairo', sans-serif;
}

[data-testid="stSidebar"]{
    background:linear-gradient(180deg, #07111f 0%, #050a12 100%);
    border-right:1px solid rgba(35,53,83,.9);
}
[data-testid="stSidebar"] *{color:var(--fa-text) !important;}
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1500px;}

h1,h2,h3,.stSubheader{color:var(--fa-text) !important; font-family:'Cairo', sans-serif;}
p, span, label, div{font-family:'Cairo', sans-serif;}

.fa-hero{
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:24px;
    padding:28px 30px;
    border:1px solid rgba(23,183,232,.28);
    border-radius:24px;
    background:
        linear-gradient(135deg, rgba(17,26,43,.98) 0%, rgba(8,17,30,.98) 100%);
    box-shadow:0 18px 50px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.05);
    margin-bottom:24px;
    position:relative;
    overflow:hidden;
}
.fa-hero:before{
    content:"";
    position:absolute;
    width:220px;height:220px;
    right:-80px;top:-90px;
    background:radial-gradient(circle, rgba(23,183,232,.22), transparent 68%);
}
.fa-title{
    font-size:38px;
    line-height:1.15;
    font-weight:900;
    letter-spacing:.2px;
    color:var(--fa-text);
    margin:0;
}
.fa-title span{color:var(--fa-gold);}
.fa-subtitle{font-size:16px;color:var(--fa-muted);margin-top:8px;font-weight:700;}
.fa-meta{display:inline-block;margin-top:16px;padding:7px 12px;border-radius:999px;background:rgba(23,183,232,.12);border:1px solid rgba(23,183,232,.28);color:#bfefff;font-size:13px;font-weight:800;}
.fa-watermark{font-size:13px;color:var(--fa-muted);font-weight:800;text-align:right;}

.metric-card {
    border:1px solid rgba(35,53,83,.95);
    border-radius:20px;
    padding:18px;
    background:linear-gradient(180deg, rgba(17,26,43,.98), rgba(11,18,32,.98));
    box-shadow:0 12px 32px rgba(0,0,0,.26), inset 0 1px 0 rgba(255,255,255,.04);
    min-height:132px;
    position:relative;
    overflow:hidden;
}
.metric-card:after{
    content:"";
    position:absolute;
    left:0;right:0;bottom:0;height:2px;
    background:linear-gradient(90deg, transparent, rgba(23,183,232,.55), transparent);
}
.card-title {font-size:14px; color:#9cc9ff; margin-bottom:10px; font-weight:800;}
.card-value {font-size:29px; font-weight:900; color:var(--fa-gold); line-height:1.2;}
.card-note {font-size:13px; color:var(--fa-muted); margin-top:9px; font-weight:700;}
.good {border-right:7px solid var(--fa-green);}
.neutral {border-right:7px solid var(--fa-amber);}
.bad {border-right:7px solid var(--fa-red);}
.blue {border-right:7px solid var(--fa-cyan);}

.badge{
    display:inline-block;
    padding:7px 13px;
    border-radius:999px;
    font-size:13px;
    font-weight:900;
    margin:4px 5px 4px 0;
    border:1px solid rgba(255,255,255,.08);
}
.badge-green {background:rgba(18,209,142,.14); color:#7cf0bd;}
.badge-yellow {background:rgba(245,158,11,.14); color:#ffd166;}
.badge-red {background:rgba(255,77,90,.14); color:#ff9ca4;}
.badge-blue {background:rgba(23,183,232,.14); color:#8be7ff;}

.report-box{
    direction:rtl;
    text-align:right;
    white-space:pre-wrap;
    line-height:2;
    border:1px solid rgba(35,53,83,.95);
    border-radius:22px;
    padding:26px;
    background:linear-gradient(180deg, rgba(17,26,43,.98), rgba(8,17,30,.98));
    color:var(--fa-text);
    font-size:16px;
    box-shadow:0 14px 36px rgba(0,0,0,.22);
}
.telegram-box{
    border:1px solid rgba(23,183,232,.28);
    border-radius:18px;
    padding:16px;
    background:rgba(23,183,232,.08);
    color:#bfefff;
    font-weight:800;
}

[data-testid="stMetricValue"]{color:var(--fa-gold) !important;}
.stButton button, .stDownloadButton button{
    border-radius:12px;
    border:1px solid rgba(23,183,232,.35);
    background:linear-gradient(135deg, #0b6b8f, #0b3b63);
    color:white;
    font-weight:900;
}
.stTextInput input{
    background:#0b1220;
    color:var(--fa-text);
    border:1px solid var(--fa-border);
}
[data-testid="stTabs"] button {color:var(--fa-muted); font-weight:800;}
[data-testid="stDataFrame"]{border-radius:16px; overflow:hidden;}
hr{border-color:rgba(35,53,83,.75);}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

COT_FALLBACK = {
    "valid": True,
    "source": "CFTC Legacy Futures Only, Last Available Fallback",
    "status": "Last Available Data",
    "date": "2026-06-09",
    "long": 207984,
    "short": 34147,
    "net": 173837,
    "change": -2183,
    "score": 80,
    "bias": "bullish",
    "trend4": "positive",
    "strength": 82,
}

# ---------------- Helpers ----------------
def fmt_num(x, digits=2):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "No data"
    try:
        return f"{float(x):,.{digits}f}"
    except Exception:
        return str(x)


def fmt_int(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "No data"
    try:
        return f"{int(round(float(x))):,}"
    except Exception:
        return str(x)


def ar_bias(bias):
    return {"bullish": "صاعد", "bearish": "هابط", "neutral": "محايد"}.get(str(bias).lower(), "محايد")


def ar_gold_bias(bias):
    return {"bullish": "صاعد للذهب", "bearish": "هابط للذهب", "neutral": "محايد"}.get(str(bias).lower(), "محايد")


def css_class(bias):
    b = str(bias).lower()
    if b == "bullish":
        return "good"
    if b == "bearish":
        return "bad"
    return "neutral"


def badge(text, kind="blue"):
    return f'<span class="badge badge-{kind}">{text}</span>'


def metric_card(title, value, note, bias="neutral"):
    st.markdown(
        f"""
        <div class="metric-card {css_class(bias)}">
            <div class="card-title">{title}</div>
            <div class="card-value">{value}</div>
            <div class="card-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def classify_score(score):
    if score >= 80:
        return "Strong Bullish", "bullish", "شراء التصحيحات فقط", "Low to Medium"
    if score >= 65:
        return "Bullish", "bullish", "شراء التصحيحات", "Medium"
    if score > 35:
        return "Neutral", "neutral", "انتظار تأكيد من الشارت", "Medium"
    if score > 20:
        return "Bearish", "bearish", "بيع الارتدادات", "Medium"
    return "Strong Bearish", "bearish", "بيع الارتدادات فقط", "Medium to High"


def safe_last(df, col="Close"):
    if df is None or df.empty or col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    return float(s.iloc[-1]) if len(s) else None


def safe_change_pct(df, lookback=5, col="Close"):
    if df is None or df.empty or col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if len(s) <= lookback:
        return None
    return float((s.iloc[-1] / s.iloc[-1 - lookback] - 1) * 100)


def component_score(change_pct, weight, positive_when_down=False, neutral_band=0.15):
    if change_pct is None or math.isnan(change_pct):
        return None, "neutral"
    direction = -change_pct if positive_when_down else change_pct
    if abs(direction) < neutral_band:
        return weight * 0.5, "neutral"
    if direction > 0:
        return weight, "bullish"
    return 0, "bearish"


def build_signal(name, value, change_pct, weight, positive_when_down=False, neutral_band=0.15, source="", date=None):
    score, bias = component_score(change_pct, weight, positive_when_down, neutral_band)
    valid = score is not None
    if not valid:
        score = 0
        bias = "neutral"
    return {
        "name": name,
        "value": value,
        "change_pct": change_pct,
        "weight": weight,
        "score": score,
        "bias": bias,
        "valid": valid,
        "source": source,
        "date": date,
    }

# ---------------- Data Sources ----------------
@st.cache_data(ttl=CACHE_TTL)
def yf_hist(symbol, period="1y"):
    df = yf.download(symbol, period=period, interval="1d", auto_adjust=False, progress=False, threads=False)
    if df is None or df.empty:
        raise ValueError(f"No data for {symbol}")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index()
    if "Date" not in df.columns:
        df.rename(columns={df.columns[0]: "Date"}, inplace=True)
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["Close"])


@st.cache_data(ttl=CACHE_TTL)
def fred_series(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url)
    df.columns = ["Date", "Value"]
    df["Date"] = pd.to_datetime(df["Date"])
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df.dropna()


@st.cache_data(ttl=60 * 60 * 6)
def cot_gold_history(limit=80):
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
    params = {
        "$limit": limit,
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "cftc_contract_market_code": "088691",
    }
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError("COT data not found")
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"], errors="coerce")
    for c in ["noncomm_positions_long_all", "noncomm_positions_short_all"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date", "noncomm_positions_long_all", "noncomm_positions_short_all"])
    df["net"] = df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"]
    df = df.sort_values("date")
    df["change"] = df["net"].diff()
    return df


def cot_signal():
    try:
        df = cot_gold_history()
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        net = float(latest["net"])
        change = float(latest["net"] - prev["net"])
        trend4 = float(latest["net"] - df.iloc[-5]["net"]) if len(df) >= 5 else change
        window = df.tail(52)["net"]
        strength = 50
        if window.max() != window.min():
            strength = float((net - window.min()) / (window.max() - window.min()) * 100)
        bias = "bullish" if net > 0 and trend4 >= -15000 else "bearish" if trend4 < -15000 else "neutral"
        return {
            "valid": True,
            "source": "CFTC Legacy Futures Only",
            "status": "Updated",
            "date": latest["date"].strftime("%Y-%m-%d"),
            "long": int(latest["noncomm_positions_long_all"]),
            "short": int(latest["noncomm_positions_short_all"]),
            "net": int(net),
            "change": int(change),
            "trend4": "positive" if trend4 >= 0 else "negative",
            "trend4_value": int(trend4),
            "strength": round(strength, 1),
            "score": 80 if bias == "bullish" else 20 if bias == "bearish" else 50,
            "bias": bias,
            "df": df,
        }
    except Exception:
        fb = COT_FALLBACK.copy()
        fb["df"] = pd.DataFrame()
        return fb


def get_market_data():
    data = {}
    sources = {}
    errors = []

    def load_first(key, candidates):
        last_err = None
        for sym, label in candidates:
            try:
                df = yf_hist(sym)
                if df is not None and not df.empty:
                    data[key] = df
                    sources[key] = label
                    return
            except Exception as e:
                last_err = e
        errors.append(f"{key}: {last_err}")
        data[key] = pd.DataFrame()
        sources[key] = "No data"

    # Gold and Silver: try spot first, then futures fallback so the platform never shows No Data.
    load_first("gold", [("XAUUSD=X", "Yahoo Finance XAUUSD Spot"), ("GC=F", "Yahoo Finance GC=F fallback")])
    load_first("silver", [("XAGUSD=X", "Yahoo Finance XAGUSD Spot"), ("SI=F", "Yahoo Finance SI=F fallback")])
    load_first("dxy", [("DX-Y.NYB", "Yahoo Finance DX-Y.NYB")])
    load_first("vix", [("^VIX", "Yahoo Finance ^VIX")])
    load_first("hui", [("^HUI", "Yahoo Finance ^HUI")])
    load_first("gld", [("GLD", "Yahoo Finance GLD")])

    try:
        data["real"] = fred_series("DFII10")
        sources["real"] = "FRED DFII10"
    except Exception as e:
        errors.append(f"Real Yield: {e}")
        data["real"] = pd.DataFrame()
        sources["real"] = "No data"
    try:
        data["us10y"] = fred_series("DGS10")
        sources["us10y"] = "FRED DGS10"
    except Exception as e:
        errors.append(f"US10Y: {e}")
        data["us10y"] = pd.DataFrame()
        sources["us10y"] = "No data"
    return data, sources, errors

def fred_change(df, lookback=5):
    if df is None or df.empty:
        return None, None
    s = df.dropna(subset=["Value"])
    if len(s) <= lookback:
        return None, None
    last = float(s.iloc[-1]["Value"])
    prev = float(s.iloc[-1 - lookback]["Value"])
    return last, last - prev


def calc_daily_signals(data, sources=None):
    sources = sources or {}
    signals = []
    dxy = data.get("dxy", pd.DataFrame())
    vix = data.get("vix", pd.DataFrame())
    hui = data.get("hui", pd.DataFrame())
    gold = data.get("gold", pd.DataFrame())
    silver = data.get("silver", pd.DataFrame())

    dxy_last = safe_last(dxy); dxy_ch = safe_change_pct(dxy, 5)
    signals.append(build_signal("DXY", dxy_last, dxy_ch, 25, positive_when_down=True, neutral_band=0.12, source=sources.get("dxy", "Yahoo Finance DX-Y.NYB"), date=dxy["Date"].iloc[-1] if not dxy.empty else None))

    real_last, real_ch_abs = fred_change(data.get("real", pd.DataFrame()), 5)
    real_ch_pct = real_ch_abs if real_ch_abs is not None else None
    signals.append(build_signal("Real Yield 10Y", real_last, real_ch_pct, 25, positive_when_down=True, neutral_band=0.04, source=sources.get("real", "FRED DFII10"), date=data.get("real", pd.DataFrame())["Date"].iloc[-1] if not data.get("real", pd.DataFrame()).empty else None))

    vix_last = safe_last(vix); vix_ch = safe_change_pct(vix, 5)
    signals.append(build_signal("VIX", vix_last, vix_ch, 15, positive_when_down=False, neutral_band=2.0, source=sources.get("vix", "Yahoo Finance ^VIX"), date=vix["Date"].iloc[-1] if not vix.empty else None))

    ratio_df = pd.DataFrame()
    ratio_last = ratio_ch = None
    if not gold.empty and not silver.empty:
        ratio_df = gold[["Date", "Close"]].merge(silver[["Date", "Close"]], on="Date", suffixes=("_gold", "_silver"))
        ratio_df["Close"] = ratio_df["Close_gold"] / ratio_df["Close_silver"]
        ratio_last = safe_last(ratio_df)
        ratio_ch = safe_change_pct(ratio_df, 5)
    signals.append(build_signal("Gold/Silver Ratio", ratio_last, ratio_ch, 15, positive_when_down=False, neutral_band=0.30, source=f"{sources.get("gold", "Gold")} / {sources.get("silver", "Silver")}", date=ratio_df["Date"].iloc[-1] if not ratio_df.empty else None))

    hui_last = safe_last(hui); hui_ch = safe_change_pct(hui, 5)
    signals.append(build_signal("HUI Index", hui_last, hui_ch, 10, positive_when_down=False, neutral_band=0.80, source=sources.get("hui", "Yahoo Finance ^HUI"), date=hui["Date"].iloc[-1] if not hui.empty else None))

    gold_last = safe_last(gold); gold_ch = safe_change_pct(gold, 5)
    signals.append(build_signal("Gold Momentum", gold_last, gold_ch, 10, positive_when_down=False, neutral_band=0.50, source=sources.get("gold", "Yahoo Finance XAUUSD/GC"), date=gold["Date"].iloc[-1] if not gold.empty else None))

    valid_weight = sum(s["weight"] for s in signals if s["valid"])
    score_sum = sum(s["score"] for s in signals if s["valid"])
    score = round(score_sum / valid_weight * 100, 1) if valid_weight else 50.0
    reliability = round(valid_weight, 1)
    return signals, score, reliability, ratio_df


def market_regime(signals, vix_value=None):
    by_name = {s["name"]: s for s in signals}
    dxy_b = by_name.get("DXY", {}).get("bias", "neutral")
    real_b = by_name.get("Real Yield 10Y", {}).get("bias", "neutral")
    vix_b = by_name.get("VIX", {}).get("bias", "neutral")
    if vix_value is not None and vix_value >= 22:
        return "Risk Off", "السوق يميل للحذر بسبب ارتفاع VIX. الذهب يستفيد إذا لم يصعد الدولار والعوائد معاً."
    if vix_b == "bullish" and (dxy_b == "bullish" or real_b == "bullish"):
        return "Risk Off", "ارتفاع الخوف مع ضغط أقل من الدولار أو العوائد يدعم الذهب دفاعياً."
    if dxy_b == "bearish" and real_b == "bearish":
        return "Dollar/Yield Pressure", "الدولار والعوائد يتحركان ضد الذهب. تجنب مطاردة الشراء قبل تأكيد فني."
    if dxy_b == "bullish" and real_b == "bullish":
        return "Gold Supportive", "الدولار أو العوائد لا يضغطان بقوة على الذهب. التصحيحات تستحق المتابعة."
    return "Neutral", "السوق مختلط. اعتمد على مستويات السيولة والفريم الكبير قبل الدخول."


def build_narrative(score, bias, strategy, risk, regime_name, signals, cot, confidence=None):
    by = {sig["name"]: sig for sig in signals}

    def factor_line(name):
        sig = by.get(name, {})
        value = fmt_num(sig.get("value"), 2)
        change = sig.get("change_pct")
        change_txt = "لا توجد قراءة تغير" if change is None else f"تغير 5 أيام: {fmt_num(change, 2)}"
        return f"• {name}: {ar_gold_bias(sig.get('bias', 'neutral'))}. القراءة الحالية: {value}. {change_txt}."

    conf = confidence if confidence is not None else min(95, round(55 + abs(score - 50) * 1.3, 1))
    cot_status = cot.get("status", "Updated")
    cot_date = cot.get("date", "No date")
    cot_net = fmt_int(cot.get("net"))
    cot_change = fmt_int(cot.get("change"))
    cot_bias = ar_gold_bias(cot.get("bias", "neutral"))

    if bias == "bullish":
        summary = "يميل السياق اليومي للذهب إلى الصعود. الأفضلية تكون لشراء التصحيحات بعد ظهور تأكيد فني واضح."
        action = "راقب مناطق الطلب والخصم، وانتظر Sweep أو MSS أو عودة إلى FVG قبل الدخول."
        invalidation = "تضعف القراءة إذا صعد الدولار والعوائد الحقيقية مع هبوط HUI أو كسر الذهب مناطق طلب رئيسية."
    elif bias == "bearish":
        summary = "يميل السياق اليومي للذهب إلى الهبوط. الأفضلية تكون لبيع الارتدادات وعدم مطاردة الهبوط من مناطق متأخرة."
        action = "راقب مناطق العرض والعلاوة، وانتظر Sweep أو MSS هابط أو رفض واضح من FVG قبل الدخول."
        invalidation = "تضعف القراءة إذا هبط الدولار والعوائد الحقيقية مع تحسن HUI وعودة الطلب على الذهب."
    else:
        summary = "السياق اليومي للذهب محايد. السوق لا يعطي أفضلية قوية قبل تأكيد السعر على الشارت."
        action = "انتظر اكتمال نموذج واضح على TradingView. لا تعتمد على القراءة العامة وحدها عند غياب الاتجاه."
        invalidation = "يتحول السياق لصاعد أو هابط عند تحرك DXY وReal Yield وVIX باتجاه واحد يدعم نفس القراءة."

    return f"""النظرة اليومية للذهب من أكاديمية فلو

الملخص التنفيذي:
{summary}

الدرجة اليومية: {fmt_num(score, 1)}/100
الانحياز اليومي: {ar_bias(bias)}
الخطة المفضلة: {strategy}
نسبة الثقة: {fmt_num(conf, 1)}%
مستوى المخاطرة: {risk}
بيئة السوق: {regime_name}
موثوقية البيانات: تعتمد على المصادر المتاحة داخل لوحة البيانات.

قراءة العوامل اليومية:
{factor_line('DXY')}
{factor_line('Real Yield 10Y')}
{factor_line('VIX')}
{factor_line('Gold/Silver Ratio')}
{factor_line('HUI Index')}
{factor_line('Gold Momentum')}

فلتر COT الأسبوعي:
• القراءة: {cot_bias}.
• صافي مراكز الصناديق: {cot_net} عقد.
• التغير الأسبوعي: {cot_change} عقد.
• آخر تحديث: {cot_date}.
• حالة المصدر: {cot_status}.

الخطة العملية:
{action}

شروط التفعيل:
• لا تدخل قبل ظهور تأكيد فني من السعر.
• الأفضل انتظار Sweep واضح للسيولة أو MSS أو عودة منظمة إلى FVG.
• راقب توافق القراءة اليومية مع DXY والعوائد الحقيقية قبل اختيار الاتجاه.

إلغاء القراءة:
{invalidation}

هذا تحليل وليس توصية.
"""

def chart_line(df, x, y, title):
    if df is None or df.empty or y not in df.columns:
        st.info(f"لا توجد بيانات كافية لعرض {title}")
        return
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[x], y=df[y], mode="lines", name=title))
    fig.update_layout(title=title, height=320, margin=dict(l=20, r=20, t=45, b=20), paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)


def historical_score_backtest(data, days=90):
    try:
        gold = data["gold"][["Date", "Close"]].rename(columns={"Close": "gold"})
        dxy = data["dxy"][["Date", "Close"]].rename(columns={"Close": "dxy"})
        vix = data["vix"][["Date", "Close"]].rename(columns={"Close": "vix"})
        hui = data["hui"][["Date", "Close"]].rename(columns={"Close": "hui"})
        silver = data["silver"][["Date", "Close"]].rename(columns={"Close": "silver"})
        df = gold.merge(dxy, on="Date", how="inner").merge(vix, on="Date", how="inner").merge(hui, on="Date", how="inner").merge(silver, on="Date", how="inner")
        real = data["real"][["Date", "Value"]].rename(columns={"Value": "real"})
        df = pd.merge_asof(df.sort_values("Date"), real.sort_values("Date"), on="Date", direction="backward")
        df["ratio"] = df["gold"] / df["silver"]
        for col in ["gold", "dxy", "vix", "hui", "ratio"]:
            df[f"{col}_ch5"] = (df[col] / df[col].shift(5) - 1) * 100
        df["real_ch5"] = df["real"] - df["real"].shift(5)

        def row_score(r):
            comps = [
                component_score(r["dxy_ch5"], 25, True, 0.12)[0],
                component_score(r["real_ch5"], 25, True, 0.04)[0],
                component_score(r["vix_ch5"], 15, False, 2.0)[0],
                component_score(r["ratio_ch5"], 15, False, 0.30)[0],
                component_score(r["hui_ch5"], 10, False, 0.80)[0],
                component_score(r["gold_ch5"], 10, False, 0.50)[0],
            ]
            comps = [c for c in comps if c is not None]
            return sum(comps) if comps else np.nan

        df["score"] = df.apply(row_score, axis=1)
        df["bias"] = np.where(df["score"] >= 65, "Bullish", np.where(df["score"] <= 35, "Bearish", "Neutral"))
        df["next_return"] = (df["gold"].shift(-1) / df["gold"] - 1) * 100
        df["match"] = np.where((df["bias"] == "Bullish") & (df["next_return"] > 0), 1, np.where((df["bias"] == "Bearish") & (df["next_return"] < 0), 1, np.where(df["bias"] == "Neutral", np.nan, 0)))
        out = df.dropna(subset=["score"]).tail(days)
        return out
    except Exception:
        return pd.DataFrame()

# ---------------- Sidebar ----------------
st.sidebar.markdown("### Flow Academy")
logo_path = Path("logo.png")
if logo_path.exists():
    st.sidebar.image(str(logo_path), use_container_width=True)
else:
    st.sidebar.info("ارفع الشعار باسم logo.png داخل GitHub")

if st.sidebar.button("تحديث البيانات"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(APP_VERSION)
st.sidebar.caption("Daily Score يعتمد على بيانات يومية. COT فلتر أسبوعي فقط.")

st.sidebar.markdown("---")
st.sidebar.markdown("### Telegram Alerts")
def secret_value(key):
    try:
        return st.secrets.get(key, "")
    except Exception:
        return ""

tg_token_secret = secret_value("TELEGRAM_BOT_TOKEN")
tg_chat_secret = secret_value("TELEGRAM_CHAT_ID")
tg_token_input = st.sidebar.text_input("Bot Token", type="password", placeholder="يفضل حفظه في Streamlit Secrets")
tg_chat_input = st.sidebar.text_input("Chat ID", placeholder="مثال: 123456789")
tg_token = tg_token_input.strip() or str(tg_token_secret).strip()
tg_chat = tg_chat_input.strip() or str(tg_chat_secret).strip()
if tg_token and tg_chat:
    st.sidebar.success("Telegram جاهز")
else:
    st.sidebar.info("أدخل Bot Token و Chat ID أو احفظهما في Secrets")

# ---------------- Load ----------------
with st.spinner("جاري تحديث بيانات Flow Academy Gold Terminal..."):
    data, sources, errors = get_market_data()
    signals, daily_score, reliability, ratio_df = calc_daily_signals(data, sources)
    cot = cot_signal()

label, daily_bias, preferred_strategy, risk_level = classify_score(daily_score)
confidence = min(95, round(55 + abs(daily_score - 50) * 1.3, 1))
vix_value = next((s["value"] for s in signals if s["name"] == "VIX"), None)
regime_name, regime_note = market_regime(signals, vix_value)
weekly_bias = cot.get("bias", "neutral")
intraday_bias = daily_bias if confidence >= 35 else "neutral"

# ---------------- Header ----------------
hero_time = datetime.utcnow().strftime("%H:%M UTC, %d %b %Y")
st.markdown(
    f"""
    <div class="fa-hero">
        <div>
            <div class="fa-title">Flow Academy <span>Daily Gold Terminal</span></div>
            <div class="fa-subtitle">لوحة احترافية لقراءة السياق اليومي والمؤسساتي للذهب</div>
            <div class="fa-meta">آخر تحديث: {hero_time}</div>
        </div>
        <div class="fa-watermark">
            COT • Real Yield • DXY • VIX • HUI • Gold/Silver<br>
            Powered by Flow Academy Intelligence
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

b_kind = "green" if daily_bias == "bullish" else "red" if daily_bias == "bearish" else "yellow"
st.markdown(
    badge(f"Daily Bias: {ar_bias(daily_bias)}", b_kind)
    + badge(f"Weekly Bias: {ar_bias(weekly_bias)}", "green" if weekly_bias == "bullish" else "red" if weekly_bias == "bearish" else "yellow")
    + badge(f"Market Regime: {regime_name}", "blue")
    + badge(f"Reliability: {fmt_num(reliability, 0)}%", "blue"),
    unsafe_allow_html=True,
)

# ---------------- Daily Plan ----------------
st.subheader("Flow Academy Daily Plan")
cols = st.columns(4)
with cols[0]:
    metric_card("Daily Context Score", f"{fmt_num(daily_score, 1)}/100", label, daily_bias)
with cols[1]:
    metric_card("Preferred Strategy", preferred_strategy, f"Confidence {fmt_num(confidence, 1)}%", daily_bias)
with cols[2]:
    metric_card("Risk Level", risk_level, regime_note, "neutral")
with cols[3]:
    metric_card("Market Regime", regime_name, regime_note, "blue")

# ---------------- Heat Map ----------------
st.subheader("Gold Heat Map")
heat_cols = st.columns(6)
for i, s in enumerate(signals):
    with heat_cols[i % 6]:
        val = fmt_num(s["value"], 2)
        ch = "No change" if s["change_pct"] is None else f"5D: {fmt_num(s['change_pct'], 2)}"
        metric_card(s["name"], val, f"{ar_gold_bias(s['bias'])} | {ch}", s["bias"])

# ---------------- Bias Section ----------------
st.subheader("Flow Academy Bias")
cols = st.columns(3)
with cols[0]:
    metric_card("Weekly Bias", ar_bias(weekly_bias), f"COT Status: {cot.get('status', 'Updated')}", weekly_bias)
with cols[1]:
    metric_card("Daily Bias", ar_bias(daily_bias), f"Score: {fmt_num(daily_score, 1)}", daily_bias)
with cols[2]:
    metric_card("Intraday Bias", ar_bias(intraday_bias), "يحتاج تأكيد من TradingView", intraday_bias)

# ---------------- COT Professional ----------------
st.subheader("COT Professional Filter")
cols = st.columns(5)
with cols[0]:
    metric_card("Net Position", fmt_int(cot.get("net")), f"Date: {cot.get('date')}", cot.get("bias", "neutral"))
with cols[1]:
    metric_card("Weekly Change", fmt_int(cot.get("change")), "Non-Commercial Net", cot.get("bias", "neutral"))
with cols[2]:
    metric_card("Long", fmt_int(cot.get("long")), cot.get("source", "CFTC"), "blue")
with cols[3]:
    metric_card("Short", fmt_int(cot.get("short")), cot.get("status", "Updated"), "blue")
with cols[4]:
    metric_card("Positioning Strength", f"{fmt_num(cot.get('strength'), 1)}%", f"4W Trend: {cot.get('trend4')}", cot.get("bias", "neutral"))

if isinstance(cot.get("df"), pd.DataFrame) and not cot.get("df").empty:
    cot_chart = cot["df"].copy().tail(52)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cot_chart["date"], y=cot_chart["net"], mode="lines+markers", name="COT Net"))
    fig.update_layout(title="COT Net Position, Last 52 Weeks", height=330, margin=dict(l=20, r=20, t=45, b=20), paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("COT يعمل حالياً من آخر قراءة محفوظة. سيعرض الرسم عند نجاح الاتصال المباشر مع CFTC.")

# ---------------- Historical Accuracy ----------------
st.subheader("Historical Accuracy, Last 90 Trading Days")
hist = historical_score_backtest(data, 90)
if not hist.empty:
    total = len(hist)
    bullish_days = int((hist["bias"] == "Bullish").sum())
    bearish_days = int((hist["bias"] == "Bearish").sum())
    neutral_days = int((hist["bias"] == "Neutral").sum())
    evaluated = hist.dropna(subset=["match"])
    acc = float(evaluated["match"].mean() * 100) if len(evaluated) else np.nan
    cols = st.columns(4)
    cols[0].metric("Bullish Days", bullish_days)
    cols[1].metric("Bearish Days", bearish_days)
    cols[2].metric("Neutral Days", neutral_days)
    cols[3].metric("Next-Day Match", "No data" if math.isnan(acc) else f"{acc:.1f}%")
    chart_line(hist, "Date", "score", "Daily Score History")
else:
    st.info("لا توجد بيانات كافية لحساب الاختبار التاريخي حالياً.")

# ---------------- Narrative ----------------
st.subheader("Flow Academy AI Narrative")
report = build_narrative(daily_score, daily_bias, preferred_strategy, risk_level, regime_name, signals, cot, confidence)
st.markdown(f'<div class="report-box">{report}</div>', unsafe_allow_html=True)
with st.expander("نسخة قابلة للنسخ"):
    st.text_area("انسخ التقرير من هنا", report, height=320)
st.download_button("تحميل التقرير TXT", data=report, file_name="flow_academy_gold_report.txt", mime="text/plain")

# ---------------- Charts ----------------
st.subheader("Market Charts")
tabs = st.tabs(["Gold", "DXY", "Real Yield", "VIX", "HUI", "Gold/Silver"])
with tabs[0]:
    chart_line(data.get("gold"), "Date", "Close", sources.get("gold", "Gold"))
with tabs[1]:
    chart_line(data.get("dxy"), "Date", "Close", "DXY")
with tabs[2]:
    chart_line(data.get("real"), "Date", "Value", "Real Yield 10Y, FRED DFII10")
with tabs[3]:
    chart_line(data.get("vix"), "Date", "Close", "VIX")
with tabs[4]:
    chart_line(data.get("hui"), "Date", "Close", "HUI Index")
with tabs[5]:
    chart_line(ratio_df, "Date", "Close", "Gold/Silver Ratio")

# ---------------- Telegram Alerts ----------------
st.subheader("Telegram Alert System")
alert_text = f"""Flow Academy Gold Terminal
Daily Bias: {ar_bias(daily_bias)}
Daily Score: {fmt_num(daily_score, 1)}/100
Preferred Plan: {preferred_strategy}
Confidence: {fmt_num(confidence, 1)}%
Risk Level: {risk_level}
Market Regime: {regime_name}
COT Weekly Bias: {ar_bias(weekly_bias)}

هذا تحليل وليس توصية."""

def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    return requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=20)

if tg_token and tg_chat:
    st.markdown('<div class="telegram-box">Telegram جاهز. اضغط الزر لإرسال اختبار مباشر إلى القناة أو الحساب.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("إرسال اختبار Telegram"):
            try:
                resp = send_telegram_message(tg_token, tg_chat, alert_text)
                if resp.ok:
                    st.success("تم إرسال التنبيه إلى Telegram.")
                else:
                    st.error(f"فشل الإرسال: {resp.text[:300]}")
            except Exception as e:
                st.error(f"Telegram error: {e}")
    with c2:
        st.caption("إذا فشل الإرسال، تحقق من Bot Token و Chat ID، وتأكد أن البوت مضاف للقناة أو أنك بدأت محادثة معه.")
else:
    st.info("Telegram غير مفعل. أدخل Bot Token و Chat ID من القائمة الجانبية، أو احفظهما في Streamlit Secrets باسم TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID.")

# ---------------- Source Quality ----------------
st.subheader("Source Quality")
source_rows = []
for s in signals:
    source_rows.append({
        "Tool": s["name"],
        "Source": s["source"],
        "Last Date": str(pd.to_datetime(s["date"]).date()) if s.get("date") is not None else "No data",
        "Status": "OK" if s["valid"] else "No Data",
        "Bias": ar_gold_bias(s["bias"]),
        "Weight": s["weight"],
    })
source_rows.append({"Tool": "COT", "Source": cot.get("source"), "Last Date": cot.get("date"), "Status": cot.get("status"), "Bias": ar_gold_bias(cot.get("bias")), "Weight": "Weekly Filter"})
st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)

if errors:
    st.warning("بعض المصادر لم تعمل حالياً:\n" + "\n".join(errors))
