"""
Gap-and-Hold Range Screener — Streamlit web app
-------------------------------------------------
Run locally:
    pip install streamlit yfinance pandas
    streamlit run app.py

Deploy free (so you can open it from your phone anytime):
    1. Push this file + requirements.txt to a GitHub repo
    2. Go to share.streamlit.io -> New app -> connect the repo
    3. You get a permanent URL, e.g. yourname-screener.streamlit.app

Pattern rule:
  Day 1 (gap day): opens with a gap (up OR down) of at least GAP_THRESHOLD_PCT
                   vs previous close. This candle's High/Low = "the range".
  Day 2, Day 3   : neither candle's High may exceed Day-1 High, nor its Low
                   go below Day-1 Low. Touching exactly is fine — only
                   breaking BEYOND it is a violation.
"""

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Gap-and-Hold Screener", layout="wide")

# ------------------------- SECTOR WATCHLISTS -------------------------
# NOTE: NSE sectoral indices are rebalanced twice a year (cut-offs: Jan 31 &
# Jul 31). These lists are the current constituents as of building this app -
# treat them as a starting point and edit freely if a stock is added/removed
# later. Symbols below are plain NSE tickers (the app adds ".NS" itself).

SECTOR_LISTS = {
    "CNXIT": [
        "COFORGE", "HCLTECH", "INFY", "LTM", "MPHASIS", "OFSS",
        "PERSISTENT", "TCS", "TECHM", "WIPRO",
    ],
    "CNXFINANCE": [
        "AXISBANK", "BSE", "BAJFINANCE", "BAJAJFINSV", "CHOLAFIN",
        "HDFCLIFE", "HDFCBANK", "ICICIGI", "ICICIPRULI", "ICICIBANK",
        "JIOFIN", "KOTAKBANK", "LICHSGFIN", "MUTHOOTFIN", "PFC",
        "RECLTD", "SBICARD", "SBILIFE", "SHRIRAMFIN", "SBIN",
    ],
    "NIFTYPVTBANK": [
        "AXISBANK", "BANDHANBNK", "HDFCBANK", "IDFCFIRSTB", "ICICIBANK",
        "INDUSINDBK", "KOTAKBANK", "RBLBANK", "FEDERALBNK", "YESBANK",
    ],
    "CNXPSUBANK": [
        "BANKBARODA", "BANKINDIA", "MAHABANK", "CANBK", "CENTRALBK",
        "INDIANB", "PSB", "IOB", "PNB", "SBIN", "UCOBANK", "UNIONBANK",
    ],
    "CNXMETAL": [
        "ADANIENT", "APLAPOLLO", "HINDALCO", "HINDCOPPER", "HINDZINC",
        "JSL", "JINDALSTEL", "JSWSTEEL", "LLOYDSME", "NATIONALUM",
        "NMDC", "SAIL", "TATASTEEL", "VEDL", "WELCORP",
    ],
    "CNXAUTO": [
        "ASHOKLEY", "BAJAJ-AUTO", "BHARATFORG", "BOSCHLTD", "EICHERMOT",
        "EXIDEIND", "HEROMOTOCO", "M&M", "MARUTI", "MOTHERSON",
        "SONACOMS", "TMPV", "TIINDIA", "TVSMOTOR", "UNOMINDA",
    ],
    "CNXFMCG": [
        "BRITANNIA", "COLPAL", "DABUR", "EMAMILTD", "HINDUNILVR", "ITC",
        "MARICO", "NESTLEIND", "PATANJALI", "RADICO", "TATACONSUM",
        "UBL", "UNITDSPR", "VBL",
    ],
    "CNXENERGY": [
        "ABB", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "ATGL",
        "AEGISLOG", "BHEL", "BPCL", "CGPOWER", "CASTROLIND", "CESC",
        "COALINDIA", "GVT&D", "GAIL", "GUJGASLTD", "GSPL", "HINDPETRO",
        "POWERINDIA", "IOC", "IGL", "INOXWIND", "JPPOWER", "JSWENERGY",
        "MGL", "NHPC", "NLCINDIA", "NTPC", "ONGC", "OIL", "PETRONET",
        "POWERGRID", "RELIANCE", "RPOWER", "ENRIN", "SIEMENS", "SJVN",
        "SUZLON", "TATAPOWER", "THERMAX", "TORNTPOWER",
    ],
    "CNXPHARMA": [
        "ABBOTINDIA", "AJANTPHARM", "ALKEM", "AUROPHARMA", "BIOCON",
        "CIPLA", "DIVISLAB", "DRREDDY", "GLAND", "GLENMARK", "IPCALAB",
        "JBCHEPHARM", "LAURUSLABS", "LUPIN", "MANKIND", "PPLPHARMA",
        "SUNPHARMA", "TORNTPHARM", "WOCKPHARMA", "ZYDUSLIFE",
    ],
    "NIFTY_HEALTHCARE": [
        "ABBOTINDIA", "ALKEM", "APOLLOHOSP", "AUROPHARMA", "BIOCON",
        "CIPLA", "DIVISLAB", "DRREDDY", "FORTIS", "GLENMARK", "IPCALAB",
        "LAURUSLABS", "LUPIN", "MANKIND", "MAXHEALTH", "PPLPHARMA",
        "SUNPHARMA", "SYNGENE", "TORNTPHARM", "ZYDUSLIFE",
    ],
    "NIFTY_CAPITAL_MKT": [
        "360ONE", "ABSLAMC", "ANANDRATHI", "ANGELONE", "BSE", "CDSL",
        "CAMS", "HDFCAMC", "IEX", "KFINTECH", "MOTILALOFS", "MCX",
        "NAM_INDIA", "NUVAMA", "UTIAMC",
    ],
    "NIFTY_IND_DEFENCE": [
        "ASTRAMICRO", "BEML", "BDL", "BEL", "BHARATFORG", "COCHINSHIP",
        "CYIENTDLM", "DATAPATTNS", "DYNAMATECH", "GRSE", "HAL",
        "MTARTECH", "MAZDOCK", "MIDHANI", "PARAS", "SOLARINDS",
        "UNIMECH", "ZENTEC",
    ],
    "NIFTY_CONSR_DURBL": [
        "AMBER", "BATAINDIA", "BLUESTARCO", "CENTURYPLY", "CERA",
        "CROMPTON", "DIXON", "HAVELLS", "KAJARIACER", "KALYANKJIL",
        "PGEL", "TITAN", "VGUARD", "VOLTAS", "WHIRLPOOL",
    ],
    "NIFTY_CHEMICALS": [
        "AARTIIND", "ATUL", "BAYERCROP", "CHAMBLFERT", "COROMANDEL",
        "DEEPAKFERT", "DEEPAKNTR", "FLUOROCHEM", "HSCL", "LINDEINDIA",
        "NAVINFLUOR", "PCBL", "PIIND", "PIDILITIND", "SOLARINDS", "SRF",
        "SUMICHEM", "SWANCORP", "TATACHEM", "UPL",
    ],
    "CPSE": [
        "BEL", "COALINDIA", "COCHINSHIP", "NBCC", "NHPC", "NLCINDIA",
        "NTPC", "ONGC", "OIL", "POWERGRID", "SJVN",
    ],
    "CNXMEDIA": [
        "DBCORP", "HATHWAY", "NAZARA", "NETWORK18", "PVRINOX", "PFOCUS",
        "SAREGAMA", "SUNTV", "TIPSMUSIC", "ZEEL",
    ],
    "NIFTY_MS_IT_TELCM": [
        "AFFLE", "BHARTIHEXA", "BSOFT", "COFORGE", "CYIENT", "HFCL",
        "HEXT", "INDUSTOWER", "INTELLECT", "KPITTECH", "LTTS", "MPHASIS",
        "OFSS", "PERSISTENT", "SONATSOFTW", "TATACOMM", "TATAELXSI",
        "TATATECH", "ZENSARTECH",
    ],
    "CNXREALTY": [
        "ANANTRAJ", "BRIGADE", "DLF", "GODREJPROP", "LODHA",
        "OBEROIRLTY", "PRESTIGE", "SIGNATURE", "SOBHA", "PHOENIXLTD",
    ],
    "NIFTY_IND_TOURISM": [
        "BLS", "CHALET", "DEVYANI", "EIHOTEL", "GMRAIRPORT", "ITCHOTELS",
        "IRCTC", "INDIGO", "JUBLFOOD", "THELEELA", "LEMONTREE",
        "SAPPHIRE", "TBOTEK", "INDHOTEL", "DBREALTY", "VENTIVE",
    ],
    "Custom (fill your own)": [],
}

# ------------------------- SIDEBAR CONTROLS -------------------------

st.sidebar.header("Watchlist")

sector_choice = st.sidebar.selectbox(
    "Pick a sector — stocks load automatically",
    options=list(SECTOR_LISTS.keys()),
)

symbols = list(SECTOR_LISTS[sector_choice])
symbol_to_sector = {sym: sector_choice for sym in symbols}

st.sidebar.caption(f"📋 {len(symbols)} stock(s) in current watchlist")
if symbols:
    with st.sidebar.expander("View current watchlist"):
        st.write(", ".join(symbols))

st.sidebar.header("Settings")

gap_threshold = st.sidebar.number_input(
    "Minimum gap % (either direction)", value=0.4, step=0.1, min_value=0.0
)
confirm_candles = st.sidebar.number_input(
    "Candles that must hold the range after gap day", value=2, step=1, min_value=1
)
history_period = st.sidebar.selectbox(
    "History to fetch per symbol", options=["1mo", "3mo", "6mo", "1y", "2y"], index=2
)

with st.sidebar.container(key="run_scan_btn_wrap"):
    run_button = st.button("🔍 Run Scan", type="primary", use_container_width=True)

# Sector color palette for the stacked bar chart (mirrors Chartink's
# colored-legend style)
SECTOR_COLORS = {
    "CNXIT": "#29ABE2",
    "CNXFINANCE": "#F4511E",
    "NIFTYPVTBANK": "#E91E63",
    "CNXPSUBANK": "#8E24AA",
    "CNXMETAL": "#43A047",
    "CNXAUTO": "#1E88E5",
    "CNXFMCG": "#FB8C00",
    "CNXENERGY": "#FDD835",
    "CNXPHARMA": "#00ACC1",
    "NIFTY_HEALTHCARE": "#7B1FA2",
    "NIFTY_CAPITAL_MKT": "#6D4C41",
    "NIFTY_IND_DEFENCE": "#26A69A",
    "NIFTY_CONSR_DURBL": "#EC407A",
    "NIFTY_CHEMICALS": "#00796B",
    "CPSE": "#5C6BC0",
    "CNXMEDIA": "#FF7043",
    "NIFTY_MS_IT_TELCM": "#42A5F5",
    "CNXREALTY": "#9CCC65",
    "NIFTY_IND_TOURISM": "#AB47BC",
    "Custom (fill your own)": "#78909C",
    "n/a": "#B0BEC5",
}


def get_expected_trading_date():
    """
    Returns the date that 'Latest Result' should match against, based on
    real-world IST day/time:
      - Monday to Friday: today's own date (strict, no fallback)
      - Saturday: Friday's date (market was closed today)
      - Sunday, before 11:55 PM IST: Friday's date
      - Sunday, after 11:55 PM IST: None -> nothing should show
        (Monday's own session hasn't happened/updated yet)
    """
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    weekday = now_ist.weekday()  # Monday=0 ... Sunday=6
    today_date = now_ist.date()

    if weekday <= 4:  # Monday(0) - Friday(4)
        return today_date
    elif weekday == 5:  # Saturday
        return today_date - timedelta(days=1)  # last Friday
    else:  # Sunday (6)
        cutoff = now_ist.replace(hour=23, minute=55, second=0, microsecond=0)
        if now_ist <= cutoff:
            return today_date - timedelta(days=2)  # last Friday
        return None


# ------------------------- CORE LOGIC -------------------------


def find_all_patterns(df: pd.DataFrame, gap_pct_min: float, confirm_n: int) -> list[dict]:
    """Scan the ENTIRE history given (not just recent days) and return every
    time the gap-and-hold pattern FULLY completed - gap day + all confirm_n
    candles held inside the range. Partial/still-forming setups (where we
    don't yet have enough candles to confirm) are NOT included."""
    df = df.reset_index(drop=True)
    n = len(df)
    matches = []

    for i in range(1, n):
        prev_close = float(df["Close"].iloc[i - 1])
        gap_pct = (float(df["Open"].iloc[i]) - prev_close) / prev_close * 100

        if abs(gap_pct) < gap_pct_min:
            continue

        # not enough candles left after the gap day to fully confirm yet - skip
        if i + confirm_n >= n:
            continue

        range_high = float(df["High"].iloc[i])
        range_low = float(df["Low"].iloc[i])

        broken = False
        for j in range(i + 1, i + 1 + confirm_n):
            if float(df["High"].iloc[j]) > range_high or float(df["Low"].iloc[j]) < range_low:
                broken = True
                break

        if broken:
            continue  # setup invalidated - do NOT include

        complete_idx = i + confirm_n
        complete_close = float(df["Close"].iloc[complete_idx])
        prev_day_close = float(df["Close"].iloc[complete_idx - 1])
        complete_pct_change = round((complete_close - prev_day_close) / prev_day_close * 100, 2)
        complete_volume = int(df["Volume"].iloc[complete_idx]) if "Volume" in df.columns else None

        matches.append({
            "gap_pct": round(gap_pct, 2),
            "range_high": range_high,
            "range_low": range_low,
            "status": "CONFIRMED",
            "confirmed_candles": confirm_n,
            "gap_date": str(df["Date"].iloc[i].date()) if "Date" in df.columns else str(i),
            "confirm_complete_date": str(df["Date"].iloc[complete_idx].date()) if "Date" in df.columns else str(complete_idx),
            "close": round(complete_close, 2),
            "pct_change": complete_pct_change,
            "volume": complete_volume,
        })

    return matches


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_history(symbol: str, period: str) -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval="1d", progress=False, auto_adjust=True)
    if not df.empty:
        # newer yfinance versions return MultiIndex columns even for a
        # single symbol (e.g. ('Close', 'INFY.NS')) - flatten them so the
        # rest of the code can treat columns as plain 'Close', 'Open', etc.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
    return df


def run_screener(symbols: list[str], gap_pct_min: float, confirm_n: int, period: str) -> pd.DataFrame:
    rows = []
    progress = st.progress(0.0, text="Scanning...")
    for idx, sym in enumerate(symbols):
        ticker = f"{sym.strip().upper()}.NS"
        try:
            df = fetch_history(ticker, period)
            if not df.empty:
                matches = find_all_patterns(df, gap_pct_min, confirm_n)
                for pattern in matches:
                    pattern["symbol"] = sym.strip().upper()
                    rows.append(pattern)
        except Exception as e:
            st.warning(f"Skipped {sym}: {e}")
        progress.progress((idx + 1) / len(symbols), text=f"Scanning... {sym}")
    progress.empty()

    cols = ["symbol", "gap_date", "confirm_complete_date", "status", "gap_pct",
            "range_low", "range_high", "confirmed_candles", "close", "pct_change", "volume"]
    result = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)
    if not result.empty:
        # most recent occurrences first, like Chartink's backtest view
        result = result.sort_values("gap_date", ascending=False).reset_index(drop=True)
    return result


# ------------------------- MAIN PAGE -------------------------

st.markdown("""
<style>
    .app-title-banner {
        background: linear-gradient(90deg, #e6396b 0%, #ff7e5f 50%, #ffb347 100%);
        padding: 18px 28px;
        border-radius: 14px;
        color: white;
        margin-bottom: 18px;
    }
    .app-title-banner h1 {
        color: white !important;
        margin: 0;
        font-size: 26px;
    }
    h3 { color: #d6336c !important; }
    section[data-testid="stSidebar"] {
        background-color: #F7F8FA;
        border-right: 1px solid #e5e7eb;
    }
    /* default button color (Run Scan) - pink/orange */
    .stButton>button {
        background: linear-gradient(90deg, #e6396b, #ff7e5f);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #d6336c, #ff6b47);
        color: white;
    }
    /* Prev/Next buttons - blue/purple */
    .st-key-prevnext_btn_wrap .stButton>button {
        background: linear-gradient(90deg, #4f46e5, #7c3aed);
    }
    .st-key-prevnext_btn_wrap .stButton>button:hover {
        background: linear-gradient(90deg, #4338ca, #6d28d9);
    }
    /* Download button - green/teal */
    div[data-testid="stDownloadButton"] button {
        background: linear-gradient(90deg, #10b981, #059669);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background: linear-gradient(90deg, #0d9488, #047857);
        color: white;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
    }
</style>
<div class="app-title-banner">
    <h1>📊 Gap-and-Hold Range Screener</h1>
</div>
""", unsafe_allow_html=True)

if run_button:
    if not symbols:
        st.error("Pick at least one sector to build your watchlist.")
    else:
        result_df = run_screener(symbols, gap_threshold, confirm_candles, history_period)
        if not result_df.empty:
            result_df["sector"] = result_df["symbol"].map(symbol_to_sector).fillna("n/a")
        st.session_state["result_df"] = result_df
        st.session_state.pop("selected_date_idx", None)  # reset navigation on a fresh scan
        st.session_state.pop("_last_click_raw", None)
        st.session_state["show_detail"] = False

if "result_df" in st.session_state:
    result_df = st.session_state["result_df"]
    expected_date = get_expected_trading_date()

    # ---- Latest Result: CONFIRMED setups whose confirmation completed on expected_date ----
    st.subheader("🔎 Latest Result")
    if expected_date is None or result_df.empty:
        st.info("NO STOCK PRESENT")
    else:
        today_confirmed = result_df[result_df["confirm_complete_date"] == str(expected_date)].copy()
        if today_confirmed.empty:
            st.info("NO STOCK PRESENT")
        else:
            display_df = today_confirmed[["symbol", "close", "pct_change", "volume"]].rename(columns={
                "symbol": "SYMBOL", "close": "CLOSE", "pct_change": "%CHANGE", "volume": "VOLUME",
            }).sort_values("SYMBOL").reset_index(drop=True)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    if result_df.empty:
        st.info("No qualifying patterns found in the current watchlist / history window.")
    else:
        st.subheader("📜 Backtest History")

        counts_by_date = (
            result_df.groupby("confirm_complete_date")["symbol"]
            .nunique()
            .reset_index(name="count")
            .sort_values("confirm_complete_date")
        )
        all_dates_sorted = counts_by_date["confirm_complete_date"].tolist()

        show_detail = st.session_state.get("show_detail", False)

        if not show_detail:
            # ---- Excel-style horizontal scrollbar (slider) to move through history ----
            WINDOW_SIZE = 30
            max_start = max(0, len(all_dates_sorted) - WINDOW_SIZE)
            if max_start > 0:
                scroll_pos = st.slider(
                    "Scroll through history", min_value=0, max_value=max_start,
                    value=max_start, step=1, key="chart_scroll",
                )
            else:
                scroll_pos = 0
            visible_dates = all_dates_sorted[scroll_pos:scroll_pos + WINDOW_SIZE]

            # group by date AND sector for the stacked, color-coded bars (Chartink style)
            counts_by_date_sector = (
                result_df.groupby(["confirm_complete_date", "sector"])["symbol"]
                .nunique()
                .reset_index(name="count")
            )
            chart_df = counts_by_date_sector[counts_by_date_sector["confirm_complete_date"].isin(visible_dates)].copy()
            chart_df["date_dt"] = pd.to_datetime(chart_df["confirm_complete_date"])

            fig = px.bar(
                chart_df, x="date_dt", y="count", color="sector",
                color_discrete_map=SECTOR_COLORS,
            )
            fig.update_layout(
                template="plotly_white",
                paper_bgcolor="white",
                plot_bgcolor="white",
                xaxis_title=None, yaxis_title=None,
                height=400, margin=dict(l=10, r=10, t=10, b=10),
                hoverlabel=dict(bgcolor="white", font_size=13, bordercolor="#e6396b"),
                dragmode=False,  # no drag/pan directly on chart - use the slider above instead
                barmode="stack",
                bargap=0.55,  # thin bars, like the reference screenshot
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5,
                    title=None,
                ),
            )
            visible_dt = pd.to_datetime(visible_dates)
            fig.update_xaxes(
                type="date",
                range=[visible_dt.min() - pd.Timedelta(days=2), visible_dt.max() + pd.Timedelta(days=2)],
                fixedrange=True,
                tickformat="%b %d",
                showgrid=True, gridcolor="#eef0f4",
                rangebreaks=[dict(bounds=["sat", "mon"])],  # skip weekends - no trading, no gaps
            )
            fig.update_yaxes(fixedrange=True, showgrid=True, gridcolor="#eef0f4")
            fig.update_traces(marker_line_width=0, hovertemplate="<b>%{x|%d-%m-%Y}</b><br>%{fullData.name}: %{y}<extra></extra>")

            click_event = st.plotly_chart(
                fig, use_container_width=True, on_select="rerun",
                selection_mode="points", key="backtest_chart",
                config={
                    "scrollZoom": False,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": [
                        "zoomIn2d", "zoomOut2d", "zoom2d", "autoScale2d",
                        "resetScale2d", "lasso2d", "select2d", "pan2d",
                    ],
                    "doubleClick": False,
                },
            )

            if click_event and click_event.get("selection", {}).get("points"):
                raw_clicked = click_event["selection"]["points"][0].get("x")
                # only act if this is a genuinely NEW click - otherwise the chart's
                # persisted selection state re-fires on the very next rerun and
                # would immediately flip us right back into detail view
                if raw_clicked != st.session_state.get("_last_click_raw"):
                    st.session_state["_last_click_raw"] = raw_clicked
                    clicked_date = str(pd.to_datetime(raw_clicked).date())
                    if clicked_date in all_dates_sorted:
                        st.session_state["selected_date_idx"] = all_dates_sorted.index(clicked_date)
                        st.session_state["show_detail"] = True
                        st.rerun()

        else:
            # ---- Detail view: Back button + Prev/Next + Symbol/Date table only ----
            if st.button("← Back"):
                st.session_state["show_detail"] = False
                st.rerun()

            idx = st.session_state["selected_date_idx"]

            with st.container(key="prevnext_btn_wrap"):
                col_l, col_prev, col_next, col_r = st.columns([4, 1, 1, 4])
                with col_prev:
                    if st.button("<< Prev", disabled=(idx <= 0)):
                        st.session_state["selected_date_idx"] = max(0, idx - 1)
                        st.rerun()
                with col_next:
                    if st.button("Next >>", disabled=(idx >= len(all_dates_sorted) - 1)):
                        st.session_state["selected_date_idx"] = min(len(all_dates_sorted) - 1, idx + 1)
                        st.rerun()

            selected_date = all_dates_sorted[st.session_state["selected_date_idx"]]
            day_df = result_df[result_df["confirm_complete_date"] == selected_date][
                ["symbol", "confirm_complete_date"]
            ].rename(columns={"symbol": "SYMBOL", "confirm_complete_date": "DATE"}).sort_values("SYMBOL").reset_index(drop=True)

            # custom compact table - light blue header, alternating light blue/white
            # rows, no grid lines (matches the reference look)
            table_rows = "".join(
                f'<tr style="background-color: {"#EAF2FF" if i % 2 else "#FFFFFF"};">'
                f'<td style="padding:8px 16px; color:#2563eb; font-weight:500;">{row.SYMBOL}</td>'
                f'<td style="padding:8px 16px; color:#374151;">{row.DATE}</td>'
                f'</tr>'
                for i, row in enumerate(day_df.itertuples())
            )
            st.markdown(f"""
            <table style="width:320px; border-collapse:collapse; font-size:14px; border-radius:8px; overflow:hidden;">
                <thead>
                    <tr style="background-color:#DCE9FF;">
                        <th style="text-align:left; padding:8px 16px; color:#1f2937; width:160px;">Symbol</th>
                        <th style="text-align:left; padding:8px 16px; color:#1f2937; width:160px;">Date</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
            """, unsafe_allow_html=True)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download full history as CSV", csv, "results.csv", "text/csv")
else:
    st.info("Edit your watchlist and settings on the left, then click **Run Scan**.")
