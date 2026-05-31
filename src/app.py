"""
Position Tracker — Trade journal, risk metrics, paper trading
Run with: streamlit run position_tracker.py
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime, date
from pathlib import Path
import plotly.graph_objects as go

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="Position Tracker",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
)

DATA_FILE = Path("trades_data.json")

# ============================================================
# CSS — match the HTML aesthetic
# ============================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, .stApp, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
}
.stApp { background: #FAFAF7; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.block-container { padding-top: 1.5rem; max-width: 1400px; }

/* App title */
.app-title {
    font-size: 26px; font-weight: 600; letter-spacing: -0.02em;
    color: #1A1A1A; margin: 0; display: flex; align-items: center; gap: 12px;
}
.app-title::before {
    content: ''; width: 6px; height: 24px; background: #1A1A1A; display: inline-block;
}
.app-subtitle {
    font-size: 11px; color: #8F8F87; text-transform: uppercase;
    letter-spacing: 0.12em; font-family: 'IBM Plex Mono', monospace;
    margin: 4px 0 0 18px;
}

/* Metric card */
.metric-card {
    background: white; border: 1px solid #E5E5DD; border-radius: 8px;
    padding: 14px 16px; height: 100%;
}
.metric-label {
    font-size: 10px; color: #8F8F87; text-transform: uppercase;
    letter-spacing: 0.1em; font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 6px;
}
.metric-value {
    font-size: 22px; font-weight: 500;
    font-family: 'IBM Plex Mono', monospace;
    font-feature-settings: 'tnum'; color: #1A1A1A;
}
.metric-sub {
    font-size: 11px; color: #8F8F87; margin-top: 4px;
    font-family: 'IBM Plex Mono', monospace;
}
.pos { color: #15803D !important; }
.neg { color: #B91C1C !important; }

/* Position card */
.pos-card {
    background: white; border: 1px solid #E5E5DD; border-radius: 8px;
    padding: 16px; margin-bottom: 8px;
}
.pos-card.paper { border-left: 3px solid #B45309; }
.pos-card.closed { background: #F4F4EE; }

.pc-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.pc-head-left { flex: 1; }
.pc-ticker { font-size: 16px; font-weight: 600; letter-spacing: -0.01em; color: #1A1A1A; }
.pc-tags { margin-top: 6px; }
.tag {
    font-size: 10px; font-weight: 500; padding: 2px 6px;
    border-radius: 3px; text-transform: uppercase; letter-spacing: 0.04em;
    font-family: 'IBM Plex Mono', monospace; margin-right: 4px;
    display: inline-block;
}
.tag-long { background: #DCFCE7; color: #15803D; }
.tag-short { background: #FEE2E2; color: #B91C1C; }
.tag-paper { background: #FEF3C7; color: #B45309; }
.tag-closed { background: #EBEBE2; color: #5B5B58; }
.tag-setup { background: #DBEAFE; color: #1D4ED8; }

.pc-ret { text-align: right; font-family: 'IBM Plex Mono', monospace; }
.pc-ret-pct { font-size: 20px; font-weight: 600; line-height: 1; }
.pc-ret-r { font-size: 12px; margin-top: 4px; }
.pc-ret-pnl { font-size: 11px; margin-top: 2px; color: #8F8F87; }

.pc-stats {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 8px; padding: 10px; background: #F4F4EE;
    border-radius: 6px; margin: 12px 0 10px 0;
}
.pc-stat-label {
    font-size: 9px; color: #8F8F87; text-transform: uppercase;
    letter-spacing: 0.06em; font-family: 'IBM Plex Mono', monospace;
}
.pc-stat-val {
    font-size: 12px; font-weight: 500;
    font-family: 'IBM Plex Mono', monospace; margin-top: 2px;
    color: #1A1A1A;
}

/* PROMINENT remaining-position panel */
.pc-remaining {
    background: white; border: 1.5px solid #15803D;
    border-radius: 6px; padding: 10px 12px; margin: 10px 0;
}
.pc-remaining.closed { border-color: #8F8F87; }
.pc-remaining.paper { border-color: #B45309; }
.pc-remaining-title {
    font-size: 10px; color: #8F8F87; text-transform: uppercase;
    letter-spacing: 0.08em; font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 6px;
}
.pc-remaining-main {
    display: flex; justify-content: space-between; align-items: baseline;
    font-family: 'IBM Plex Mono', monospace; margin-bottom: 6px;
}
.pc-remaining-qty { font-size: 18px; font-weight: 600; color: #1A1A1A; }
.pc-remaining-qty-sub { font-size: 11px; color: #5B5B58; }
.pc-remaining-pct { font-size: 14px; font-weight: 500; color: #15803D; }
.pc-remaining.closed .pc-remaining-pct { color: #8F8F87; }
.pc-progress-bar {
    height: 6px; background: #EBEBE2; border-radius: 3px; overflow: hidden; margin-bottom: 8px;
}
.pc-progress-fill { height: 100%; background: #15803D; transition: width 0.3s; }
.pc-progress-fill.closed { background: #8F8F87; }
.pc-pnl-split {
    display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 6px;
    padding-top: 8px; border-top: 1px solid #E5E5DD;
}
.pc-pnl-label {
    font-size: 9px; color: #8F8F87; text-transform: uppercase;
    letter-spacing: 0.06em; font-family: 'IBM Plex Mono', monospace;
}
.pc-pnl-val {
    font-size: 13px; font-weight: 500;
    font-family: 'IBM Plex Mono', monospace; margin-top: 2px;
}

.pc-info {
    display: flex; justify-content: space-between;
    font-size: 11px; color: #5B5B58; margin-top: 6px;
    font-family: 'IBM Plex Mono', monospace;
}

/* Exit history */
.exit-history {
    margin-top: 10px; padding-top: 10px;
    border-top: 1px solid #E5E5DD;
}
.exit-history-title {
    font-size: 10px; color: #8F8F87; text-transform: uppercase;
    letter-spacing: 0.08em; font-family: 'IBM Plex Mono', monospace;
    margin-bottom: 6px;
}
.exit-row {
    display: grid; grid-template-columns: 90px 80px 50px 1fr 70px;
    gap: 8px; font-size: 11px; padding: 4px 0;
    font-family: 'IBM Plex Mono', monospace;
    border-bottom: 1px dashed #E5E5DD;
}
.exit-row:last-child { border-bottom: none; }
.exit-row-header { color: #8F8F87; font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; }

/* Section heading */
.section-head {
    font-size: 12px; text-transform: uppercase;
    letter-spacing: 0.12em; font-weight: 500; color: #5B5B58;
    font-family: 'IBM Plex Mono', monospace;
    margin: 24px 0 12px 0;
}

/* Streamlit button polish */
.stButton button {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    border-radius: 6px !important;
    padding: 4px 10px !important;
    min-height: 32px !important;
    border-color: #C8C8BD !important;
}
.stButton button:hover { background: #F4F4EE !important; border-color: #5B5B58 !important; }
.stButton button[kind="primary"] { background: #1A1A1A !important; border-color: #1A1A1A !important; color: white !important; }
.stButton button[kind="primary"]:hover { background: #000 !important; }

/* Sidebar polish */
[data-testid="stSidebar"] { background: white; border-right: 1px solid #E5E5DD; }

/* Dataframe */
[data-testid="stDataFrame"] { font-family: 'IBM Plex Mono', monospace; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: white; border: 1px solid #E5E5DD; border-radius: 6px; padding: 3px; }
.stTabs [data-baseweb="tab"] {
    font-family: 'IBM Plex Sans', sans-serif; font-size: 13px; font-weight: 500;
    padding: 6px 14px; border-radius: 4px; color: #5B5B58;
}
.stTabs [aria-selected="true"] { background: #1A1A1A !important; color: white !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# STATE
# ============================================================
def default_state():
    return {
        "positions": [
            {
                "id": 1,
                "ticker": "CEMPRO",
                "side": "long",
                "entry": 893.575,
                "stop": 820,
                "qty": 2200,
                "cmp": 1071.15,
                "date": "2026-05-26",
                "target": 1200,
                "paper": False,
                "setup": "Breakout",
                "notes": "",
                "exits": [
                    {"price": 1000, "qty": 750, "date": "2026-05-28", "note": "T1 hit"}
                ],
            },
            {
                "id": 2,
                "ticker": "NETWEB",
                "side": "long",
                "entry": 4170.99,
                "stop": 3950,
                "qty": 1700,
                "cmp": 4629,
                "date": "2026-05-23",
                "target": 5200,
                "paper": False,
                "setup": "VCP",
                "notes": "",
                "exits": [
                    {
                        "price": 4500,
                        "qty": 425,
                        "date": "2026-05-27",
                        "note": "Partial T1",
                    }
                ],
            },
            {
                "id": 3,
                "ticker": "OMNI",
                "side": "long",
                "entry": 446.4,
                "stop": 415,
                "qty": 2700,
                "cmp": 501.45,
                "date": "2026-05-24",
                "target": 560,
                "paper": False,
                "setup": "Breakout",
                "notes": "",
                "exits": [],
            },
            {
                "id": 4,
                "ticker": "WIPRO",
                "side": "long",
                "entry": 480,
                "stop": 455,
                "qty": 500,
                "cmp": 450,
                "date": "2026-05-10",
                "target": 550,
                "paper": False,
                "setup": "Pullback",
                "notes": "",
                "exits": [
                    {
                        "price": 450,
                        "qty": 500,
                        "date": "2026-05-28",
                        "note": "Stopped out",
                    }
                ],
            },
            {
                "id": 5,
                "ticker": "NIFTY",
                "side": "long",
                "entry": 22000,
                "stop": 21500,
                "qty": 50,
                "cmp": 22800,
                "date": "2026-05-20",
                "target": 23500,
                "paper": True,
                "setup": "Index test",
                "notes": "paper trial",
                "exits": [],
            },
        ],
        "settings": {"portfolio": 5000000, "risk_pct": 1.0, "paper_in_metrics": False},
        "next_id": 6,
        "filter": "active",
    }


def load_state():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            pass
    return default_state()


def save_state():
    DATA_FILE.write_text(json.dumps(st.session_state.state, indent=2, default=str))


if "state" not in st.session_state:
    st.session_state.state = load_state()
if "edit_id" not in st.session_state:
    st.session_state.edit_id = None
if "show_add" not in st.session_state:
    st.session_state.show_add = False
if "exit_id" not in st.session_state:
    st.session_state.exit_id = None
if "price_id" not in st.session_state:
    st.session_state.price_id = None
if "show_bulk" not in st.session_state:
    st.session_state.show_bulk = False

state = st.session_state.state


# ============================================================
# HELPERS — trade math
# ============================================================
def sold_qty(p):
    return sum(e["qty"] for e in p["exits"])


def remaining_qty(p):
    return p["qty"] - sold_qty(p)


def is_closed(p):
    return remaining_qty(p) <= 0


def risk_per_share(p):
    return abs(p["entry"] - p["stop"])


def initial_risk(p):
    return risk_per_share(p) * p["qty"]


def direction(p):
    return -1 if p["side"] == "short" else 1


def realized_pnl(p):
    return sum((e["price"] - p["entry"]) * e["qty"] * direction(p) for e in p["exits"])


def unrealized_pnl(p):
    return (p["cmp"] - p["entry"]) * remaining_qty(p) * direction(p)


def total_pnl(p):
    return realized_pnl(p) + unrealized_pnl(p)


def position_value(p):
    return p["entry"] * p["qty"]


def return_pct(p):
    pv = position_value(p)
    return (total_pnl(p) / pv * 100) if pv else 0


def r_multiple(p):
    r = initial_risk(p)
    return (total_pnl(p) / r) if r else 0


def planned_rr(p):
    if not p.get("target"):
        return None
    r = risk_per_share(p)
    return (abs(p["target"] - p["entry"]) / r) if r else None


def days_held(p):
    end = (
        datetime.fromisoformat(p["exits"][-1]["date"]).date()
        if is_closed(p)
        else date.today()
    )
    start = datetime.fromisoformat(p["date"]).date()
    return max(0, (end - start).days)


# Formatters
def fmt_money(n):
    if n is None or pd.isna(n) or n != n:
        return "—"
    abs_n, sign = abs(n), "-" if n < 0 else ""
    if abs_n >= 1e7:
        return f"{sign}₹{abs_n/1e7:.2f}Cr"
    if abs_n >= 1e5:
        return f"{sign}₹{abs_n/1e5:.2f}L"
    if abs_n >= 1e3:
        return f"{sign}₹{abs_n/1e3:.1f}K"
    return f"{sign}₹{abs_n:.0f}"


def fmt_r(n):
    if n is None:
        return "—"
    return f"{'+' if n>=0 else ''}{n:.2f}R"


def fmt_pct(n):
    if n is None:
        return "—"
    return f"{'+' if n>=0 else ''}{n:.2f}%"


# ============================================================
# DIALOGS
# ============================================================
@st.dialog("Add / Edit Trade", width="large")
def trade_dialog():
    edit_id = st.session_state.edit_id
    p = (
        next((x for x in state["positions"] if x["id"] == edit_id), None)
        if edit_id
        else None
    )
    title = "Edit Trade" if p else "Add New Trade"
    st.markdown(f"**{title}**")

    c1, c2 = st.columns(2)
    with c1:
        ticker = st.text_input("Ticker", value=p["ticker"] if p else "").upper()
        entry = st.number_input(
            "Entry Price (₹)",
            value=float(p["entry"]) if p else 0.0,
            step=0.01,
            format="%.2f",
        )
        qty = st.number_input(
            "Quantity", value=int(p["qty"]) if p else 100, min_value=1, step=1
        )
        entry_date = st.date_input(
            "Entry Date",
            value=datetime.fromisoformat(p["date"]).date() if p else date.today(),
        )
        setup = st.text_input(
            "Setup / Strategy",
            value=p.get("setup", "") if p else "",
            placeholder="Breakout, VCP, Pullback...",
        )
    with c2:
        side = st.selectbox(
            "Direction",
            ["long", "short"],
            index=0 if (not p or p["side"] == "long") else 1,
        )
        stop = st.number_input(
            "Stop Loss (₹)",
            value=float(p["stop"]) if p else 0.0,
            step=0.01,
            format="%.2f",
        )
        cmp_val = st.number_input(
            "Current Price (₹)",
            value=float(p["cmp"]) if p else 0.0,
            step=0.01,
            format="%.2f",
        )
        target = st.number_input(
            "Target (₹) — optional",
            value=float(p["target"]) if (p and p.get("target")) else 0.0,
            step=0.01,
            format="%.2f",
        )
        paper = st.selectbox(
            "Trade Type", ["Live", "Paper"], index=1 if (p and p["paper"]) else 0
        )

    notes = st.text_area("Notes", value=p.get("notes", "") if p else "", height=70)

    # Show planned R:R preview if user entered target
    if entry and stop and target and entry != stop:
        rr = abs(target - entry) / abs(entry - stop)
        risk_amt = abs(entry - stop) * qty
        st.caption(
            f"Planned R:R = 1:{rr:.2f} · Initial risk = {fmt_money(risk_amt)} "
            f"({risk_amt/state['settings']['portfolio']*100:.2f}% of book)"
        )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.edit_id = None
            st.session_state.show_add = False
            st.rerun()
    with c2:
        if st.button("Save Trade", type="primary", use_container_width=True):
            if not ticker or entry <= 0 or stop <= 0 or qty <= 0:
                st.error("Fill ticker, entry, stop, and qty.")
                return
            data = {
                "ticker": ticker,
                "side": side,
                "entry": entry,
                "stop": stop,
                "qty": int(qty),
                "cmp": cmp_val if cmp_val > 0 else entry,
                "date": str(entry_date),
                "target": target if target > 0 else None,
                "setup": setup,
                "paper": (paper == "Paper"),
                "notes": notes,
            }
            if p:
                p.update(data)
            else:
                state["positions"].append({"id": state["next_id"], **data, "exits": []})
                state["next_id"] += 1
            save_state()
            st.session_state.edit_id = None
            st.session_state.show_add = False
            st.rerun()


@st.dialog("Record Exit")
def exit_dialog():
    p = next(
        (x for x in state["positions"] if x["id"] == st.session_state.exit_id), None
    )
    if not p:
        return
    rem = remaining_qty(p)
    cur_r = (
        ((p["cmp"] - p["entry"]) * direction(p)) / risk_per_share(p)
        if risk_per_share(p)
        else 0
    )

    st.markdown(
        f"**{p['ticker']}** &nbsp;·&nbsp; Entry ₹{p['entry']:.2f} &nbsp;·&nbsp; Stop ₹{p['stop']:.2f}<br>"
        f"<span style='font-family: IBM Plex Mono, monospace'>"
        f"Remaining: <strong>{rem} sh</strong> &nbsp;·&nbsp; "
        f"CMP ₹{p['cmp']:.2f} ({fmt_r(cur_r)})</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        exit_price = st.number_input(
            "Exit Price (₹)", value=float(p["cmp"]), step=0.01, format="%.2f"
        )
        exit_dt = st.date_input("Exit Date", value=date.today())
    with c2:
        exit_qty = st.number_input(
            "Quantity Sold", value=rem, min_value=1, max_value=rem, step=1
        )
        exit_note = st.text_input("Note", placeholder="T1, T2, Stopped out, Trail...")

    # Preview the impact
    if exit_price and exit_qty:
        exit_pnl = (exit_price - p["entry"]) * exit_qty * direction(p)
        exit_r = exit_pnl / (risk_per_share(p) * exit_qty) if risk_per_share(p) else 0
        new_rem = rem - exit_qty
        cls_msg = "→ position closes" if new_rem == 0 else f"→ {new_rem} sh remains"
        cls = "pos" if exit_pnl >= 0 else "neg"
        st.markdown(
            f"<div style='background:#F4F4EE; padding:8px 12px; border-radius:6px; "
            f"font-family: IBM Plex Mono, monospace; font-size:12px;'>"
            f"P&L on this exit: <span class='{cls}'><strong>{fmt_money(exit_pnl)} · {fmt_r(exit_r)}</strong></span>"
            f" &nbsp;{cls_msg}</div>",
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Cancel", use_container_width=True, key="exit_cancel"):
            st.session_state.exit_id = None
            st.rerun()
    with c2:
        if st.button(
            "Record Exit", type="primary", use_container_width=True, key="exit_save"
        ):
            if exit_qty > rem:
                st.error(f"Qty exceeds remaining ({rem})")
                return
            p["exits"].append(
                {
                    "price": exit_price,
                    "qty": int(exit_qty),
                    "date": str(exit_dt),
                    "note": exit_note,
                }
            )
            save_state()
            st.session_state.exit_id = None
            st.rerun()


@st.dialog("Update Price")
def price_dialog():
    p = next(
        (x for x in state["positions"] if x["id"] == st.session_state.price_id), None
    )
    if not p:
        return
    st.markdown(f"**{p['ticker']}** &nbsp;·&nbsp; Current CMP: ₹{p['cmp']:.2f}")
    new_price = st.number_input(
        "New CMP (₹)", value=float(p["cmp"]), step=0.01, format="%.2f"
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancel", use_container_width=True, key="price_cancel"):
            st.session_state.price_id = None
            st.rerun()
    with c2:
        if st.button(
            "Update", type="primary", use_container_width=True, key="price_save"
        ):
            p["cmp"] = new_price
            save_state()
            st.session_state.price_id = None
            st.rerun()


@st.dialog("Bulk Price Update", width="large")
def bulk_dialog():
    st.markdown(
        "Paste lines as **TICKER PRICE** — one per line. "
        "Accepts space, comma, tab, or semicolon as separator."
    )
    st.code("CEMPRO 1085\nNETWEB 4710\nOMNI 512\nNIFTY,22950", language=None)

    data = st.text_area(
        "Paste price data",
        height=200,
        key="bulk_data",
        placeholder="TICKER PRICE\nTICKER PRICE\n...",
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Cancel", use_container_width=True, key="bulk_cancel"):
            st.session_state.show_bulk = False
            st.rerun()
    with c2:
        if st.button(
            "Apply Updates", type="primary", use_container_width=True, key="bulk_save"
        ):
            import re

            updated, skipped = 0, 0
            for line in data.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = re.split(r"[\s,;\t|]+", line)
                if len(parts) < 2:
                    skipped += 1
                    continue
                try:
                    ticker = parts[0].upper()
                    price = float(parts[1])
                except ValueError:
                    skipped += 1
                    continue
                matches = [x for x in state["positions"] if x["ticker"] == ticker]
                if matches:
                    for x in matches:
                        x["cmp"] = price
                    updated += 1
                else:
                    skipped += 1
            save_state()
            st.session_state.show_bulk = False
            st.toast(
                f"Updated {updated} ticker(s)"
                + (f", skipped {skipped}" if skipped else ""),
                icon="✅",
            )
            st.rerun()


# Open dialogs based on session state
if st.session_state.show_add or st.session_state.edit_id is not None:
    trade_dialog()
if st.session_state.exit_id is not None:
    exit_dialog()
if st.session_state.price_id is not None:
    price_dialog()
if st.session_state.show_bulk:
    bulk_dialog()


# ============================================================
# SIDEBAR — settings, actions
# ============================================================
with st.sidebar:
    st.markdown("### Quick Actions")
    if st.button("➕ New Trade", use_container_width=True, type="primary"):
        st.session_state.show_add = True
        st.rerun()
    if st.button("↻ Bulk Update Prices", use_container_width=True):
        st.session_state.show_bulk = True
        st.rerun()

    st.divider()
    st.markdown("### Settings")
    new_portfolio = st.number_input(
        "Portfolio Size (₹)",
        value=int(state["settings"]["portfolio"]),
        min_value=1,
        step=10000,
        format="%d",
    )
    new_risk = st.number_input(
        "Default Risk per Trade (%)",
        value=float(state["settings"]["risk_pct"]),
        min_value=0.1,
        max_value=10.0,
        step=0.1,
        format="%.2f",
    )
    new_paper = st.checkbox(
        "Include paper trades in metrics", value=state["settings"]["paper_in_metrics"]
    )
    if (
        new_portfolio != state["settings"]["portfolio"]
        or new_risk != state["settings"]["risk_pct"]
        or new_paper != state["settings"]["paper_in_metrics"]
    ):
        state["settings"]["portfolio"] = new_portfolio
        state["settings"]["risk_pct"] = new_risk
        state["settings"]["paper_in_metrics"] = new_paper
        save_state()
        st.rerun()

    st.divider()
    st.markdown("### Export")
    df_all = pd.DataFrame(
        [
            {
                "Ticker": p["ticker"],
                "Side": p["side"],
                "Type": "Paper" if p["paper"] else "Live",
                "Entry Date": p["date"],
                "Entry": p["entry"],
                "Stop": p["stop"],
                "Qty": p["qty"],
                "CMP": p["cmp"],
                "Target": p.get("target"),
                "Setup": p.get("setup", ""),
                "Days": days_held(p),
                "Return %": round(return_pct(p), 2),
                "R": round(r_multiple(p), 2),
                "P&L": round(total_pnl(p), 0),
                "Status": "Closed" if is_closed(p) else "Open",
                "Remaining": remaining_qty(p),
                "Exits": ";".join(
                    f'{e["date"]}@{e["price"]}x{e["qty"]}' for e in p["exits"]
                ),
            }
            for p in state["positions"]
        ]
    )
    csv = df_all.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Export CSV",
        csv,
        file_name=f"trades-{date.today()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()
    if st.button("⚠ Reset all data", use_container_width=True):
        if DATA_FILE.exists():
            DATA_FILE.unlink()
        st.session_state.state = default_state()
        save_state()
        st.rerun()


# ============================================================
# HEADER
# ============================================================
st.markdown('<h1 class="app-title">Position Tracker</h1>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Trade journal · Risk metrics · Paper trading</div>',
    unsafe_allow_html=True,
)


# ============================================================
# METRICS BAR
# ============================================================
def compute_metrics():
    pool = (
        state["positions"]
        if state["settings"]["paper_in_metrics"]
        else [p for p in state["positions"] if not p["paper"]]
    )
    closed = [p for p in pool if is_closed(p)]
    open_ = [p for p in pool if not is_closed(p)]
    wins = [p for p in closed if total_pnl(p) > 0]
    losses = [p for p in closed if total_pnl(p) <= 0]

    total_pl = sum(total_pnl(p) for p in pool)
    total_return_pct = total_pl / state["settings"]["portfolio"] * 100
    win_rate = (len(wins) / len(closed) * 100) if closed else 0
    gross_win = sum(total_pnl(p) for p in wins)
    gross_loss = abs(sum(total_pnl(p) for p in losses))
    profit_factor = (
        gross_win / gross_loss if gross_loss else (float("inf") if gross_win else 0)
    )
    expectancy = sum(r_multiple(p) for p in closed) / len(closed) if closed else 0
    open_risk = sum(initial_risk(p) for p in open_)
    open_exposure = sum(p["cmp"] * remaining_qty(p) for p in open_)
    avg_win_r = sum(r_multiple(p) for p in wins) / len(wins) if wins else 0
    avg_loss_r = sum(r_multiple(p) for p in losses) / len(losses) if losses else 0

    return dict(
        pool=pool,
        closed=closed,
        open_=open_,
        wins=wins,
        losses=losses,
        total_pl=total_pl,
        total_return_pct=total_return_pct,
        win_rate=win_rate,
        gross_win=gross_win,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        expectancy=expectancy,
        open_risk=open_risk,
        open_exposure=open_exposure,
        avg_win_r=avg_win_r,
        avg_loss_r=avg_loss_r,
    )


m = compute_metrics()


def metric_card(label, value, sub, cls=""):
    return (
        f'<div class="metric-card">'
        f'<div class="metric-label">{label}</div>'
        f'<div class="metric-value {cls}">{value}</div>'
        f'<div class="metric-sub">{sub}</div></div>'
    )


cards = [
    (
        "Total P&L",
        fmt_money(m["total_pl"]),
        f"{fmt_pct(m['total_return_pct'])} of book",
        "pos" if m["total_pl"] >= 0 else "neg",
    ),
    (
        "Win Rate",
        f"{m['win_rate']:.0f}%" if m["closed"] else "—",
        f"{len(m['closed'])} closed · {len(m['wins'])}W {len(m['losses'])}L",
        "",
    ),
    (
        "Expectancy",
        fmt_r(m["expectancy"]),
        "positive edge" if m["expectancy"] >= 0 else "negative edge",
        "pos" if m["expectancy"] >= 0 else "neg",
    ),
    (
        "Profit Factor",
        f"{m['profit_factor']:.2f}" if m["profit_factor"] != float("inf") else "∞",
        "gross win / gross loss",
        "pos" if m["profit_factor"] >= 1 else "neg",
    ),
    (
        "Avg Win / Loss",
        f"{fmt_r(m['avg_win_r'])} / {fmt_r(m['avg_loss_r'])}",
        (
            f"ratio { (m['avg_win_r']/abs(m['avg_loss_r'])):.2f}"
            if m["avg_loss_r"]
            else "—"
        ),
        "",
    ),
    (
        "Open Positions",
        str(len(m["open_"])),
        f"exposure {fmt_money(m['open_exposure'])}",
        "",
    ),
    (
        "Open Risk",
        fmt_money(m["open_risk"]),
        f"{m['open_risk']/state['settings']['portfolio']*100:.2f}% of book",
        "",
    ),
    (
        "Trades Taken",
        str(len(m["pool"])),
        f"{sum(1 for p in state['positions'] if p['paper'])} paper trades",
        "",
    ),
]

cols = st.columns(4)
for i, (l, v, s, c) in enumerate(cards):
    with cols[i % 4]:
        st.markdown(metric_card(l, v, s, c), unsafe_allow_html=True)
    if i % 4 == 3 and i < len(cards) - 1:
        cols = st.columns(4)


# ============================================================
# POSITIONS
# ============================================================
st.markdown('<div class="section-head">Positions</div>', unsafe_allow_html=True)

c1, c2 = st.columns([3, 2])
with c1:
    filter_choice = st.radio(
        "Filter",
        ["Active", "Closed", "Paper", "All"],
        index=["active", "closed", "paper", "all"].index(state["filter"]),
        horizontal=True,
        label_visibility="collapsed",
    )
    new_filter = filter_choice.lower()
    if new_filter != state["filter"]:
        state["filter"] = new_filter
        save_state()
with c2:
    search = st.text_input(
        "Search", placeholder="Search ticker or setup...", label_visibility="collapsed"
    ).lower()


# Apply filter
def matches_filter(p):
    if state["filter"] == "active":
        if is_closed(p) or p["paper"]:
            return False
    elif state["filter"] == "closed":
        if not is_closed(p):
            return False
    elif state["filter"] == "paper":
        if not p["paper"]:
            return False
    if search:
        if (
            search not in p["ticker"].lower()
            and search not in (p.get("setup") or "").lower()
        ):
            return False
    return True


positions = sorted(
    [p for p in state["positions"] if matches_filter(p)],
    key=lambda p: p["date"],
    reverse=True,
)

if not positions:
    st.info("No positions match the filter. Add one via the sidebar.")
else:
    # Render in 2-column grid
    for i in range(0, len(positions), 2):
        row = st.columns(2, gap="small")
        for j, p in enumerate(positions[i : i + 2]):
            with row[j]:
                render_card_and_actions(p) if False else None  # see below


def render_card_and_actions(p):
    """Render a single position card with action buttons."""
    closed = is_closed(p)
    pnl = total_pnl(p)
    pct = return_pct(p)
    r = r_multiple(p)
    rem = remaining_qty(p)
    rem_pct = (rem / p["qty"] * 100) if p["qty"] else 0
    days = days_held(p)
    planned_rr_val = planned_rr(p)
    pct_cls = "pos" if pnl >= 0 else "neg"

    # Tags
    tags = []
    tags.append(
        '<span class="tag tag-short">Short</span>'
        if p["side"] == "short"
        else '<span class="tag tag-long">Long</span>'
    )
    if p["paper"]:
        tags.append('<span class="tag tag-paper">Paper</span>')
    if closed:
        tags.append('<span class="tag tag-closed">Closed</span>')
    if p.get("setup"):
        tags.append(f'<span class="tag tag-setup">{p["setup"]}</span>')

    card_cls = "pos-card"
    if p["paper"]:
        card_cls += " paper"
    if closed:
        card_cls += " closed"
    rem_cls = "pc-remaining"
    if closed:
        rem_cls += " closed"
    elif p["paper"]:
        rem_cls += " paper"

    # Exit history HTML
    exit_html = ""
    if p["exits"]:
        rows = [
            '<div class="exit-row exit-row-header"><span>DATE</span><span>PRICE</span>'
            "<span>QTY</span><span>NOTE</span><span>R</span></div>"
        ]
        for e in p["exits"]:
            e_pnl = (e["price"] - p["entry"]) * e["qty"] * direction(p)
            e_r = e_pnl / (risk_per_share(p) * e["qty"]) if risk_per_share(p) else 0
            r_cls = "pos" if e_pnl >= 0 else "neg"
            rows.append(
                f'<div class="exit-row"><span>{e["date"]}</span>'
                f'<span>₹{e["price"]:.2f}</span><span>{e["qty"]}</span>'
                f'<span>{e.get("note") or "—"}</span>'
                f'<span class="{r_cls}">{fmt_r(e_r)}</span></div>'
            )
        exit_html = (
            f'<div class="exit-history">'
            f'<div class="exit-history-title">Exit history · {sold_qty(p)} sh sold</div>'
            f'{"".join(rows)}</div>'
        )

    target_txt = f'₹{p["target"]:.2f}' if p.get("target") else "—"

    card_html = f"""
    <div class="{card_cls}">
        <div class="pc-head">
            <div class="pc-head-left">
                <div class="pc-ticker">{p["ticker"]}</div>
                <div class="pc-tags">{"".join(tags)}</div>
            </div>
            <div class="pc-ret">
                <div class="pc-ret-pct {pct_cls}">{fmt_pct(pct)}</div>
                <div class="pc-ret-r {pct_cls}">{fmt_r(r)}</div>
                <div class="pc-ret-pnl">{fmt_money(pnl)}</div>
            </div>
        </div>

        <div class="pc-stats">
            <div><div class="pc-stat-label">Entry</div><div class="pc-stat-val">₹{p["entry"]:.2f}</div></div>
            <div><div class="pc-stat-label">CMP</div><div class="pc-stat-val">₹{p["cmp"]:.2f}</div></div>
            <div><div class="pc-stat-label">Stop</div><div class="pc-stat-val">₹{p["stop"]:.2f}</div></div>
            <div><div class="pc-stat-label">Target</div><div class="pc-stat-val">{target_txt}</div></div>
            <div><div class="pc-stat-label">Risk/Sh</div><div class="pc-stat-val">₹{risk_per_share(p):.2f}</div></div>
            <div><div class="pc-stat-label">Init Risk</div><div class="pc-stat-val">{fmt_money(initial_risk(p))}</div></div>
            <div><div class="pc-stat-label">Pos Size</div><div class="pc-stat-val">{fmt_money(position_value(p))}</div></div>
            <div><div class="pc-stat-label">% of Book</div><div class="pc-stat-val">{position_value(p)/state["settings"]["portfolio"]*100:.1f}%</div></div>
        </div>

        <div class="{rem_cls}">
            <div class="pc-remaining-title">Position remaining</div>
            <div class="pc-remaining-main">
                <span><span class="pc-remaining-qty">{rem}</span>
                <span class="pc-remaining-qty-sub"> / {p["qty"]} shares</span></span>
                <span class="pc-remaining-pct">{rem_pct:.0f}%</span>
            </div>
            <div class="pc-progress-bar">
                <div class="pc-progress-fill {'closed' if closed else ''}" style="width:{rem_pct}%"></div>
            </div>
            <div class="pc-pnl-split">
                <div>
                    <div class="pc-pnl-label">Realized P&L · {sold_qty(p)} sh sold</div>
                    <div class="pc-pnl-val {'pos' if realized_pnl(p)>=0 else 'neg'}">{fmt_money(realized_pnl(p))}</div>
                </div>
                <div>
                    <div class="pc-pnl-label">Unrealized · {rem} sh open</div>
                    <div class="pc-pnl-val {'pos' if unrealized_pnl(p)>=0 else 'neg'}">{fmt_money(unrealized_pnl(p))}</div>
                </div>
            </div>
        </div>

        <div class="pc-info">
            <span>{days}d held · since {p["date"]}</span>
            <span>{f'RR planned 1:{planned_rr_val:.1f}' if planned_rr_val else ''}</span>
        </div>
        {exit_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # Action buttons row
    if not closed:
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("Exit", key=f"exit_{p['id']}", use_container_width=True):
                st.session_state.exit_id = p["id"]
                st.rerun()
        with b2:
            if st.button("Price", key=f"price_{p['id']}", use_container_width=True):
                st.session_state.price_id = p["id"]
                st.rerun()
        with b3:
            if st.button("Edit", key=f"edit_{p['id']}", use_container_width=True):
                st.session_state.edit_id = p["id"]
                st.rerun()
        with b4:
            if st.button("Delete", key=f"del_{p['id']}", use_container_width=True):
                state["positions"] = [
                    x for x in state["positions"] if x["id"] != p["id"]
                ]
                save_state()
                st.rerun()
    else:
        b1, b2, b3 = st.columns([1, 1, 2])
        with b1:
            if st.button("Edit", key=f"edit_{p['id']}", use_container_width=True):
                st.session_state.edit_id = p["id"]
                st.rerun()
        with b2:
            if st.button("Delete", key=f"del_{p['id']}", use_container_width=True):
                state["positions"] = [
                    x for x in state["positions"] if x["id"] != p["id"]
                ]
                save_state()
                st.rerun()
    st.write("")  # small spacer


# Render positions (now that the function is defined, redo the loop)
if positions:
    for i in range(0, len(positions), 2):
        row = st.columns(2, gap="small")
        for j, p in enumerate(positions[i : i + 2]):
            with row[j]:
                render_card_and_actions(p)


# ============================================================
# PERFORMANCE ANALYTICS
# ============================================================
st.markdown(
    '<div class="section-head">Performance Analytics</div>', unsafe_allow_html=True
)

a1, a2 = st.columns(2)

# Win/Loss profile + R distribution
with a1:
    st.markdown("**Win / Loss Profile**")
    closed = m["closed"]
    wins, losses = m["wins"], m["losses"]
    avg_win_inr = (m["gross_win"] / len(wins)) if wins else 0
    avg_loss_inr = (m["gross_loss"] / len(losses)) if losses else 0
    with_plan = [p for p in closed if planned_rr(p)]
    avg_plan_rr = (
        sum(planned_rr(p) for p in with_plan) / len(with_plan) if with_plan else 0
    )
    avg_ach_rr = (m["avg_win_r"] / abs(m["avg_loss_r"])) if m["avg_loss_r"] else 0

    stat_rows = [
        ("Trades closed", f"{len(closed)}"),
        (
            "Win rate",
            f"{m['win_rate']:.0f}%" if closed else "—",
            "pos" if m["win_rate"] >= 50 else "neg",
        ),
        ("Avg win", fmt_money(avg_win_inr), "pos"),
        ("Avg loss", fmt_money(-avg_loss_inr), "neg"),
        ("Avg win R", fmt_r(m["avg_win_r"]), "pos"),
        ("Avg loss R", fmt_r(m["avg_loss_r"]), "neg"),
        ("Planned R:R (avg)", f"1:{avg_plan_rr:.2f}" if avg_plan_rr else "—"),
        (
            "Achieved R:R",
            f"1:{avg_ach_rr:.2f}" if avg_ach_rr else "—",
            "pos" if avg_ach_rr >= 1 else "neg",
        ),
        (
            "Expectancy",
            fmt_r(m["expectancy"]),
            "pos" if m["expectancy"] >= 0 else "neg",
        ),
    ]
    rows_html = []
    for row in stat_rows:
        label, value = row[0], row[1]
        cls = row[2] if len(row) > 2 else ""
        rows_html.append(
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px solid #E5E5DD;font-size:12px;">'
            f'<span style="color:#5B5B58">{label}</span>'
            f'<span class="{cls}" style="font-family:IBM Plex Mono,monospace;font-weight:500;">{value}</span>'
            f"</div>"
        )
    st.markdown("".join(rows_html), unsafe_allow_html=True)

    # R-Multiple Distribution
    st.markdown(
        '<div style="margin-top:16px;font-weight:500">R-Multiple Distribution</div>',
        unsafe_allow_html=True,
    )
    if closed:
        buckets = {
            "<-2R": 0,
            "-2..-1R": 0,
            "-1..0R": 0,
            "0..1R": 0,
            "1..2R": 0,
            "2..3R": 0,
            ">3R": 0,
        }
        for p in closed:
            r = r_multiple(p)
            if r < -2:
                buckets["<-2R"] += 1
            elif r < -1:
                buckets["-2..-1R"] += 1
            elif r < 0:
                buckets["-1..0R"] += 1
            elif r < 1:
                buckets["0..1R"] += 1
            elif r < 2:
                buckets["1..2R"] += 1
            elif r < 3:
                buckets["2..3R"] += 1
            else:
                buckets[">3R"] += 1
        keys, vals = list(buckets.keys()), list(buckets.values())
        colors = [
            "#B91C1C",
            "#B91C1C",
            "#B91C1C",
            "#15803D",
            "#15803D",
            "#15803D",
            "#15803D",
        ]
        fig = go.Figure(
            go.Bar(
                x=keys,
                y=vals,
                marker_color=colors,
                text=[v if v else "" for v in vals],
                textposition="outside",
            )
        )
        fig.update_layout(
            height=180,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono", size=10, color="#5B5B58"),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False, visible=False),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("No closed trades yet.")

# Risk & Time + Equity Curve
with a2:
    st.markdown("**Risk & Time**")
    best_r = max((r_multiple(p) for p in closed), default=0)
    worst_r = min((r_multiple(p) for p in closed), default=0)
    avg_hold = sum(days_held(p) for p in closed) / len(closed) if closed else 0

    def streak(trades, want_win):
        srt = sorted(trades, key=lambda p: p["exits"][-1]["date"])
        mx, cur = 0, 0
        for p in srt:
            if (total_pnl(p) > 0) == want_win:
                cur += 1
                mx = max(mx, cur)
            else:
                cur = 0
        return mx

    risk_rows = [
        ("Best trade", fmt_r(best_r), "pos"),
        ("Worst trade", fmt_r(worst_r), "neg"),
        ("Avg hold (days)", f"{avg_hold:.1f}"),
        ("Win streak (max)", str(streak(closed, True)), "pos"),
        ("Loss streak (max)", str(streak(closed, False)), "neg"),
        ("Gross win", fmt_money(m["gross_win"]), "pos"),
        ("Gross loss", fmt_money(-m["gross_loss"]), "neg"),
        (
            "Net P&L",
            fmt_money(m["gross_win"] - m["gross_loss"]),
            "pos" if (m["gross_win"] - m["gross_loss"]) >= 0 else "neg",
        ),
    ]
    rows_html = []
    for row in risk_rows:
        label, value = row[0], row[1]
        cls = row[2] if len(row) > 2 else ""
        rows_html.append(
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;'
            f'border-bottom:1px solid #E5E5DD;font-size:12px;">'
            f'<span style="color:#5B5B58">{label}</span>'
            f'<span class="{cls}" style="font-family:IBM Plex Mono,monospace;font-weight:500;">{value}</span>'
            f"</div>"
        )
    st.markdown("".join(rows_html), unsafe_allow_html=True)

    st.markdown(
        '<div style="margin-top:16px;font-weight:500">Equity Curve (closed trades)</div>',
        unsafe_allow_html=True,
    )
    if closed:
        sorted_closed = sorted(closed, key=lambda p: p["exits"][-1]["date"])
        cum, points = 0, [(0, 0)]
        for i, p in enumerate(sorted_closed):
            cum += total_pnl(p)
            points.append((i + 1, cum))
        xs, ys = zip(*points)
        line_color = "#15803D" if cum >= 0 else "#B91C1C"
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                line=dict(color=line_color, width=2),
                marker=dict(size=6, color=line_color),
                fill="tozeroy",
                fillcolor=f"rgba({'21,128,61' if cum>=0 else '185,28,28'},0.08)",
            )
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#C8C8BD")
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="IBM Plex Mono", size=10, color="#5B5B58"),
            xaxis=dict(title="Closed trade #", showgrid=False),
            yaxis=dict(title="₹ cumulative", showgrid=True, gridcolor="#EBEBE2"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.caption("No closed trades yet.")


# ============================================================
# TRADE LOG
# ============================================================
st.markdown('<div class="section-head">Trade Log</div>', unsafe_allow_html=True)
df_log = pd.DataFrame(
    [
        {
            "Date": p["date"],
            "Ticker": p["ticker"],
            "Side": p["side"],
            "Type": "Paper" if p["paper"] else "Live",
            "Setup": p.get("setup", ""),
            "Entry": p["entry"],
            "Stop": p["stop"],
            "Qty": p["qty"],
            "Remaining": remaining_qty(p),
            "Days": days_held(p),
            "Return %": round(return_pct(p), 2),
            "R": round(r_multiple(p), 2),
            "P&L": round(total_pnl(p), 0),
            "Status": "Closed" if is_closed(p) else "Open",
        }
        for p in sorted(state["positions"], key=lambda x: x["date"], reverse=True)
    ]
)

if not df_log.empty:

    def color_pnl(v):
        try:
            return "color: #15803D" if float(v) >= 0 else "color: #B91C1C"
        except:
            return ""

    styled = df_log.style.map(color_pnl, subset=["Return %", "R", "P&L"])
    st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("No trades logged.")
