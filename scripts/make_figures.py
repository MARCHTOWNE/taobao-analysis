"""Read the results of sql/04–09 from MySQL and draw the charts into figures/ (or figures/en/).
从 MySQL 读取 sql/04~09 的分析结果并生成图表，输出到 figures/（英文版输出到 figures/en/）。

Usage (PowerShell, project root):
    pip install pandas matplotlib sqlalchemy pymysql
    $env:MYSQL_PASSWORD = "your root password"     # if unset, you will be prompted
    python scripts/make_figures.py              # Chinese charts -> figures/
    python scripts/make_figures.py --lang en    # English charts -> figures/en/

The SQL used by the charts is the scripts in sql/ (single source of truth); this file only fetches and draws.
图表使用的 SQL 就是 sql/ 目录里的脚本（单一来源），这里只负责取数和画图。
"""
import argparse
import getpass
import os
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

import labels

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
FIG_DIR = ROOT / "figures"

# 配色：蓝为主色，橙只用于强调（取自已校验的默认调色板）
# Palette: blue is the main color, orange is only for emphasis.
BLUE, ORANGE = "#2a78d6", "#eb6834"
FUNNEL_BLUES = ["#1c5cab", "#3987e5", "#86b6ef"]  # ordinal ramp; lightest step still has enough contrast
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

LANG = "zh"
S = labels.get("zh")


def set_lang(lang):
    global LANG, S
    LANG = lang
    S = labels.get(lang)


def setup_style(lang="zh"):
    avail = {f.name for f in font_manager.fontManager.ttflist}
    if lang == "zh":
        for name in ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "Noto Serif CJK SC"]:
            if name in avail:
                plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
                break
    else:
        plt.rcParams["font.sans-serif"] = ["Segoe UI", "Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams.update({
        "axes.unicode_minus": False,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "text.color": INK,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "font.size": 10,
    })


def style_axes(ax, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(length=0)
    if grid == "y":
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    else:
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def fmt_count(v, _=None):
    """Axis formatter: 万 for Chinese, K/M for English."""
    if LANG == "zh":
        return f"{v / 10000:.0f}万" if abs(v) >= 10000 else f"{v:.0f}"
    if abs(v) >= 1e6:
        return f"{v / 1e6:g}M"
    if abs(v) >= 1e3:
        return f"{v / 1e3:.0f}K"
    return f"{v:.0f}"


# ---------- 取数：直接复用 sql/ 里的脚本 / data: reuse the scripts in sql/ ----------
def read_statements(name):
    text = (SQL_DIR / name).read_text(encoding="utf-8")
    text = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in text.split(";") if s.strip() and not s.strip().upper().startswith("USE ")]


def to_numeric(df):
    # MySQL 的 SUM/COUNT 会返回 Decimal（object 类型），转成数值；日期等其他类型保持不变
    # MySQL returns Decimal (object dtype) for SUM/COUNT; convert those, leave dates etc. alone.
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c])
            except (ValueError, TypeError):
                pass
    return df


def tables(fetch, name):
    return [to_numeric(fetch(s)) for s in read_statements(name)]


def make_fetch():
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import URL

    pwd = os.environ.get("MYSQL_PASSWORD") or getpass.getpass("MySQL root password: ")
    url = URL.create("mysql+pymysql", username="root", password=pwd,
                     host="localhost", port=3306, database="taobao")
    engine = create_engine(url)
    return lambda stmt: pd.read_sql(text(stmt), engine)


# ---------- 图表 / charts ----------
def fig_daily(daily, out):
    d = daily.copy()
    d["label"] = pd.to_datetime(d["dt"]).dt.strftime("%m-%d")
    jump = d["uv"].iloc[-2:].mean() / d["uv"].iloc[:-2].mean() - 1
    panels = [("uv", S["daily_uv"]), ("pv", S["daily_pv"]), ("buy_cnt", S["daily_buy"])]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
    colors = [BLUE] * (len(d) - 2) + [ORANGE] * 2
    for ax, (col, title) in zip(axes, panels):
        ax.bar(d["label"], d[col], color=colors, width=0.7)
        ax.set_title(title, loc="left", fontsize=11, color=INK)
        ax.yaxis.set_major_formatter(FuncFormatter(fmt_count))
        ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        style_axes(ax)
    fig.suptitle(S["daily_title"].format(jump=jump), x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, S["sample_note"], fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def fig_hourly(h, out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
    a1.bar(h["hr"], h["pv"], color=BLUE, width=0.7)
    a1.set_title(S["hourly_pv_title"], loc="left", fontsize=11)
    a1.yaxis.set_major_formatter(FuncFormatter(fmt_count))
    a1.set_xticks(range(0, 24, 2))
    a1.set_xlabel(S["hour_xlabel"])
    style_axes(a1)
    pk = h.loc[h["pv"].idxmax()]
    a1.annotate(S["hourly_peak_pv"].format(h=int(pk["hr"])), (pk["hr"], pk["pv"]),
                xytext=(-10, 14), textcoords="offset points", ha="right", color=INK2, fontsize=9)

    a2.plot(h["hr"], h["buy_per_pv_pct"], color=BLUE, linewidth=2)
    best = h.loc[h["buy_per_pv_pct"].idxmax()]
    a2.scatter([best["hr"]], [best["buy_per_pv_pct"]], s=70, color=ORANGE,
               edgecolor=SURFACE, linewidth=2, zorder=3)
    a2.annotate(S["hourly_peak_conv"].format(h=int(best["hr"]), v=best["buy_per_pv_pct"]),
                (best["hr"], best["buy_per_pv_pct"]), xytext=(10, 6),
                textcoords="offset points", color=INK2, fontsize=9)
    a2.set_title(S["hourly_conv_title"], loc="left", fontsize=11)
    a2.set_xticks(range(0, 24, 2))
    a2.set_xlabel(S["hour_xlabel"])
    a2.set_ylim(bottom=0)
    style_axes(a2)
    fig.suptitle(S["hourly_suptitle"], x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, S["sample_note"], fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def fig_funnel(p, out):
    r = p.iloc[0]
    values = [r["pairs_pv"], r["pairs_fav_or_cart"], r["pairs_buy_after_fc"], r["pairs_direct_buy"]]
    labs = [S["funnel_s1"], S["funnel_s2"], S["funnel_s3"], S["funnel_s4"]]
    colors = FUNNEL_BLUES + [ORANGE]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    y = list(range(len(values)))[::-1]
    ax.barh(y, values, color=colors, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labs)
    ax.set_xlim(0, values[0] * 1.45)
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_count))
    for yi, v, i in zip(y, values, range(len(values))):
        if i == 1:
            note = S["funnel_note_view"].format(v=v, p=v / values[0])
        elif i == 2:
            note = S["funnel_note_fc"].format(v=v, p=v / values[1])
        elif i == 3:
            note = S["funnel_note_view"].format(v=v, p=v / values[0])
        else:
            note = f"{v:,.0f}"
        ax.text(v + values[0] * 0.012, yi, note, va="center", fontsize=9, color=INK2)
    ax.set_xlabel(S["funnel_xlabel"])
    style_axes(ax, grid="x")
    ax.set_title(S["funnel_title"], loc="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, S["sample_note"] + S["funnel_footer"], fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def fig_category(top, overall_pct, out):
    t = top.copy()
    fig, ax = plt.subplots(figsize=(10, 7))
    y = list(range(len(t)))
    ax.barh(y, t["buy_per_pv_pct"], color=BLUE, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels([S["cat_label"].format(c=c) for c in t["category_id"]], fontsize=9)
    xmax = t["buy_per_pv_pct"].max()
    ax.set_ylim(len(t) - 0.4, -1.6)  # 顶部留出放“整体”标注的空间，同时保持自上而下顺序 / room for the overall label, top-down order
    ax.axvline(overall_pct, color=ORANGE, linewidth=2, linestyle="--")
    ax.text(overall_pct + 0.06, -1.0, S["cat_overall"].format(x=overall_pct),
            color=ORANGE, fontsize=9, ha="left", va="bottom")
    ax.set_xticks(range(0, int(xmax) + 1))
    for yi, v, pv in zip(y, t["buy_per_pv_pct"], t["pv"]):
        ax.text(xmax * 1.06, yi, S["cat_value"].format(v=v, pv_wan=pv / 10000, pv_k=pv / 1000),
                va="center", fontsize=8.5, color=INK2)
    ax.set_xlabel(S["cat_xlabel"])
    ax.set_xlim(0, xmax * 1.6)
    style_axes(ax, grid="x")
    ax.set_title(S["cat_title"], loc="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, S["sample_note"] + S["cat_footer"], fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def fig_repurchase(dist, rep, out):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    total = dist["users"].sum()
    ax.bar(dist["buy_times"].astype(str), dist["users"], color=BLUE, width=0.65)
    for x, v in zip(dist["buy_times"].astype(str), dist["users"]):
        ax.text(x, v + total * 0.008, f"{v:,}\n({v / total:.0%})", ha="center", fontsize=9, color=INK2)
    ax.set_xlabel(S["rep_xlabel"])
    ax.set_ylim(0, dist["users"].max() * 1.2)
    style_axes(ax)
    rate = rep.iloc[0]["repeat_rate_pct"]
    ax.set_title(S["rep_title"].format(rate=rate), loc="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, S["sample_note"], fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def build_all(fetch, out_dir=None, lang="zh"):
    set_lang(lang)
    setup_style(lang)
    out_dir = Path(out_dir) if out_dir else (FIG_DIR if lang == "zh" else FIG_DIR / "en")
    out_dir.mkdir(parents=True, exist_ok=True)
    overview = tables(fetch, "04_overview.sql")
    trend = tables(fetch, "05_trend.sql")
    funnel = tables(fetch, "06_funnel.sql")
    cat = tables(fetch, "07_category.sql")
    rep = tables(fetch, "09_repurchase.sql")
    fig_daily(trend[0], out_dir / "01_daily_trend.png")
    fig_hourly(trend[1], out_dir / "02_hourly.png")
    fig_funnel(funnel[1], out_dir / "03_funnel_pairs.png")
    fig_category(cat[0], float(overview[1].iloc[0]["buy_per_pv_pct"]), out_dir / "04_category_conversion.png")
    fig_repurchase(rep[0], rep[1], out_dir / "05_repurchase.png")
    return sorted(p.name for p in out_dir.glob("*.png"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["zh", "en"], default="zh")
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()
    print("Generated:", build_all(make_fetch(), args.out_dir, args.lang))
