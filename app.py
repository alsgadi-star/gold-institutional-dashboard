import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Gold Institutional Dashboard", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem;}
</style>
""", unsafe_allow_html=True)

st.title("لوحة الذهب المؤسساتية")
st.caption("COT, Real Yields, HUI, Gold/Silver Ratio, GLD")

@st.cache_data(ttl=3600)
def fred_series(series_id: str):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    df = pd.read_csv(url)
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()

@st.cache_data(ttl=3600)
def stooq_daily(symbol: str):
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    df = pd.read_csv(url)
    if df.empty or "Close" not in df.columns:
        raise ValueError(f"No data for {symbol}")
    df["Date"] = pd.to_datetime(df["Date"])
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    return df.dropna()

@st.cache_data(ttl=21600)
def cot_gold():
    url = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"
    params = {
        "$limit": 5,
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "cftc_contract_market_code": "088691"
    }
    r = requests.get(url, params=params, timeout=25)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError("COT data not found")
    df = pd.DataFrame(data)
    for col in df.columns:
        if col not in ["market_and_exchange_names", "report_date_as_yyyy_mm_dd", "cftc_contract_market_code"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["report_date_as_yyyy_mm_dd"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"])
    return df.sort_values("report_date_as_yyyy_mm_dd", ascending=False)

def trend_bias(last, prev, positive_when_down=False):
    diff = last - prev
    if abs(diff) < 0.0001:
        return "Neutral", 0, diff
    if positive_when_down:
        return ("Bullish", 1, diff) if diff < 0 else ("Bearish", -1, diff)
    return ("Bullish", 1, diff) if diff > 0 else ("Bearish", -1, diff)

def label_ar(bias):
    labels = {"Bullish": "صاعد للذهب", "Bearish": "هابط للذهب", "Neutral": "محايد"}
    return labels.get(bias, "محايد")

def fmt_num(x):
    if x is None:
        return "No data"
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return str(x)

def fmt_int(x):
    if x is None:
        return "No data"
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)

score = 0
notes = []

cot_bias, net, cot_change = "Neutral", None, None
real_bias, r_last, real_diff = "Neutral", None, None
hui_bias, h_last, hui_diff = "Neutral", None, None
gs_bias, gs_last, gs_diff = "Neutral", None, None
gld_bias, g_last, gld_diff = "Neutral", None, None

try:
    cot = cot_gold()
    latest = cot.iloc[0]
    prev = cot.iloc[1] if len(cot) > 1 else latest
    nc_long = int(latest.get("noncomm_positions_long_all", 0) or 0)
    nc_short = int(latest.get("noncomm_positions_short_all", 0) or 0)
    net = nc_long - nc_short
    prev_net = int(prev.get("noncomm_positions_long_all", 0) or 0) - int(prev.get("noncomm_positions_short_all", 0) or 0)
    cot_change = net - prev_net
    cot_bias = "Bullish" if net > 0 and cot_change >= -10000 else "Bearish" if cot_change < -10000 else "Neutral"
    score += 2 if cot_bias == "Bullish" else -2 if cot_bias == "Bearish" else 0
except Exception as e:
    notes.append(f"COT error: {e}")

try:
    real = fred_series("DFII10")
    r_last = float(real.iloc[-1]["value"])
    r_prev = float(real.iloc[-6]["value"] if len(real) > 6 else real.iloc[-2]["value"])
    real_bias, real_score, real_diff = trend_bias(r_last, r_prev, positive_when_down=True)
    score += real_score * 2
except Exception as e:
    notes.append(f"Real Yield error: {e}")

try:
    hui = stooq_daily("^hui")
    h_last = float(hui.iloc[-1]["Close"])
    h_prev = float(hui.iloc[-6]["Close"] if len(hui) > 6 else hui.iloc[-2]["Close"])
    hui_bias, hui_score, hui_diff = trend_bias(h_last, h_prev)
    score += hui_score
except Exception as e:
    notes.append(f"HUI error: {e}")

try:
    gold = stooq_daily("xauusd")
    silver = stooq_daily("xagusd")
    merged = gold[["Date", "Close"]].merge(silver[["Date", "Close"]], on="Date", suffixes=("_gold", "_silver"))
    merged["ratio"] = merged["Close_gold"] / merged["Close_silver"]
    gs_last = float(merged.iloc[-1]["ratio"])
    gs_prev = float(merged.iloc[-6]["ratio"] if len(merged) > 6 else merged.iloc[-2]["ratio"])
    gs_bias, gs_score, gs_diff = trend_bias(gs_last, gs_prev)
    score += gs_score
except Exception as e:
    notes.append(f"Gold/Silver error: {e}")

try:
    gld = stooq_daily("gld.us")
    g_last = float(gld.iloc[-1]["Close"])
    g_prev = float(gld.iloc[-6]["Close"] if len(gld) > 6 else gld.iloc[-2]["Close"])
    gld_bias, gld_score, gld_diff = trend_bias(g_last, g_prev)
    score += gld_score
except Exception as e:
    notes.append(f"GLD error: {e}")

if score >= 4:
    final = "Bullish Gold Context"
elif score <= -3:
    final = "Bearish Gold Context"
else:
    final = "Neutral Gold Context"

cols = st.columns(5)
cols[0].metric("COT الصناديق", label_ar(cot_bias), f"Net {fmt_int(net)}")
cols[1].metric("Real Yield 10Y", label_ar(real_bias), f"{fmt_num(r_last)}%")
cols[2].metric("HUI Index", label_ar(hui_bias), fmt_num(h_last))
cols[3].metric("Gold/Silver", label_ar(gs_bias), fmt_num(gs_last))
cols[4].metric("GLD Proxy", label_ar(gld_bias), fmt_num(g_last))

st.subheader("النتيجة النهائية")
st.metric("Institutional Score", f"{score}/7", final)

report = """
النظرة المؤسساتية على الذهب

COT: {cot_bias}
صافي مراكز الصناديق: {net}
التغير الأسبوعي: {cot_change}

Real Yield 10Y: {real_bias}
القراءة الحالية: {real_yield}%

HUI Index: {hui_bias}
القراءة الحالية: {hui}

Gold/Silver Ratio: {gs_bias}
القراءة الحالية: {gs}

GLD Proxy: {gld_bias}
القراءة الحالية: {gld}

النتيجة النهائية: {final}
درجة القوة: {score}/7

هذا تحليل وليس توصية.
""".format(
    cot_bias=label_ar(cot_bias),
    net=fmt_int(net),
    cot_change=fmt_int(cot_change),
    real_bias=label_ar(real_bias),
    real_yield=fmt_num(r_last),
    hui_bias=label_ar(hui_bias),
    hui=fmt_num(h_last),
    gs_bias=label_ar(gs_bias),
    gs=fmt_num(gs_last),
    gld_bias=label_ar(gld_bias),
    gld=fmt_num(g_last),
    final=final,
    score=score
)

st.text_area("تقرير عربي جاهز للنشر", report, height=320)

st.subheader("الرسوم")
if "real" in locals():
    st.line_chart(real.set_index("date")["value"].tail(120))
if "merged" in locals():
    st.line_chart(merged.set_index("Date")["ratio"].tail(120))
if "hui" in locals():
    st.line_chart(hui.set_index("Date")["Close"].tail(120))

if notes:
    st.info("بعض البيانات لم تعمل من المصدر الحالي:\n" + "\n".join(notes))
