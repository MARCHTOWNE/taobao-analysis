"""从 MySQL 读取 sql/04~09 的分析结果并生成图表，输出到 figures/。

用法（PowerShell，在项目根目录）：
    pip install pandas matplotlib sqlalchemy pymysql
    $env:MYSQL_PASSWORD = "你的root密码"      # 不设置则运行时会提示输入
    python scripts/make_figures.py

图表使用的 SQL 就是 sql/ 目录里的脚本（单一来源），这里只负责取数和画图。
"""
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

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"
FIG_DIR = ROOT / "figures"

# 配色：蓝为主色，橙只用于强调（取自已校验的默认调色板）
BLUE, ORANGE = "#2a78d6", "#eb6834"
FUNNEL_BLUES = ["#1c5cab", "#3987e5", "#86b6ef"]  # 有序渐变，最浅一档对比度仍达标
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SAMPLE_NOTE = "数据：淘宝用户行为数据集，按用户抽样 5%（约 4.9 万用户），2017-11-25 至 12-03"


def setup_style():
    avail = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "Noto Serif CJK SC"]:
        if name in avail:
            plt.rcParams["font.sans-serif"] = [name, "DejaVu Sans"]
            break
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


def fmt_wan(v, _=None):
    return f"{v / 10000:.0f}万" if abs(v) >= 10000 else f"{v:.0f}"


# ---------- 取数：直接复用 sql/ 里的脚本 ----------
def read_statements(name):
    text = (SQL_DIR / name).read_text(encoding="utf-8")
    text = re.sub(r"--[^\n]*", "", text)
    return [s.strip() for s in text.split(";") if s.strip() and not s.strip().upper().startswith("USE ")]


def to_numeric(df):
    # MySQL 的 SUM/COUNT 会返回 Decimal（object 类型），转成数值；日期等其他类型保持不变
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

    pwd = os.environ.get("MYSQL_PASSWORD") or getpass.getpass("MySQL root 密码: ")
    url = URL.create("mysql+pymysql", username="root", password=pwd,
                     host="localhost", port=3306, database="taobao")
    engine = create_engine(url)
    return lambda stmt: pd.read_sql(text(stmt), engine)


# ---------- 图表 ----------
def fig_daily(daily, out):
    d = daily.copy()
    d["label"] = pd.to_datetime(d["dt"]).dt.strftime("%m-%d")
    jump = d["uv"].iloc[-2:].mean() / d["uv"].iloc[:-2].mean() - 1
    panels = [("uv", "每日访问用户数（UV）"), ("pv", "每日浏览量（PV）"), ("buy_cnt", "每日购买次数")]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6))
    colors = [BLUE] * (len(d) - 2) + [ORANGE] * 2
    for ax, (col, title) in zip(axes, panels):
        ax.bar(d["label"], d[col], color=colors, width=0.7)
        ax.set_title(title, loc="left", fontsize=11, color=INK)
        ax.yaxis.set_major_formatter(FuncFormatter(fmt_wan))
        ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        style_axes(ax)
    fig.suptitle(f"12 月 2–3 日访问用户数比此前日均高约 {jump:.0%}（橙色为这两天）",
                 x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, SAMPLE_NOTE, fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def fig_hourly(h, out):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
    a1.bar(h["hr"], h["pv"], color=BLUE, width=0.7)
    a1.set_title("各小时浏览量（9 天合计）", loc="left", fontsize=11)
    a1.yaxis.set_major_formatter(FuncFormatter(fmt_wan))
    a1.set_xticks(range(0, 24, 2))
    a1.set_xlabel("小时")
    style_axes(a1)
    pk = h.loc[h["pv"].idxmax()]
    a1.annotate(f"{int(pk['hr'])} 时浏览最多", (pk["hr"], pk["pv"]),
                xytext=(-10, 14), textcoords="offset points", ha="right", color=INK2, fontsize=9)

    a2.plot(h["hr"], h["buy_per_pv_pct"], color=BLUE, linewidth=2)
    best = h.loc[h["buy_per_pv_pct"].idxmax()]
    a2.scatter([best["hr"]], [best["buy_per_pv_pct"]], s=70, color=ORANGE,
               edgecolor=SURFACE, linewidth=2, zorder=3)
    a2.annotate(f"{int(best['hr'])} 时最高 {best['buy_per_pv_pct']:.2f}%",
                (best["hr"], best["buy_per_pv_pct"]), xytext=(10, 6),
                textcoords="offset points", color=INK2, fontsize=9)
    a2.set_title("各小时购买次数 / 浏览次数（%）", loc="left", fontsize=11)
    a2.set_xticks(range(0, 24, 2))
    a2.set_xlabel("小时")
    a2.set_ylim(bottom=0)
    style_axes(a2)
    fig.suptitle("浏览高峰在晚间，转化高峰在上午", x=0.01, ha="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, SAMPLE_NOTE, fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def fig_funnel(p, out):
    r = p.iloc[0]
    stages = [("浏览过的用户-商品对", r["pairs_pv"]),
              ("其中收藏或加购过", r["pairs_fav_or_cart"]),
              ("收藏/加购后购买", r["pairs_buy_after_fc"])]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    labels = [s[0] for s in stages] + ["未收藏/加购、直接购买"]
    values = [s[1] for s in stages] + [r["pairs_direct_buy"]]
    colors = FUNNEL_BLUES + [ORANGE]
    y = list(range(len(values)))[::-1]
    ax.barh(y, values, color=colors, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, values[0] * 1.45)
    ax.xaxis.set_major_formatter(FuncFormatter(fmt_wan))
    for yi, v, i in zip(y, values, range(len(values))):
        if i == 1:
            note = f"{v:,.0f}（占浏览 {v / values[0]:.1%}）"
        elif i == 2:
            note = f"{v:,.0f}（占收藏/加购 {v / values[1]:.1%}）"
        elif i == 3:
            note = f"{v:,.0f}（占浏览 {v / values[0]:.1%}）"
        else:
            note = f"{v:,.0f}"
        ax.text(v + values[0] * 0.012, yi, note, va="center", fontsize=9, color=INK2)
    ax.set_xlabel("用户-商品对数量")
    style_axes(ax, grid="x")
    ax.set_title("直接购买的商品数量多于收藏/加购后再购买的", loc="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, SAMPLE_NOTE + "；漏斗按“是否发生过该行为”统计，不要求时间顺序", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def fig_category(top, overall_pct, out):
    t = top.copy()
    fig, ax = plt.subplots(figsize=(10, 7))
    y = list(range(len(t)))
    ax.barh(y, t["buy_per_pv_pct"], color=BLUE, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels([f"类目 {c}" for c in t["category_id"]], fontsize=9)
    xmax = t["buy_per_pv_pct"].max()
    ax.set_ylim(len(t) - 0.4, -1.6)  # 顶部留出放“整体”标注的空间，同时保持自上而下顺序
    ax.axvline(overall_pct, color=ORANGE, linewidth=2, linestyle="--")
    ax.text(overall_pct + 0.06, -1.0, f"整体 {overall_pct:.2f}%", color=ORANGE, fontsize=9, ha="left", va="bottom")
    ax.set_xticks(range(0, int(xmax) + 1))
    for yi, v, pv in zip(y, t["buy_per_pv_pct"], t["pv"]):
        ax.text(xmax * 1.06, yi, f"{v:.2f}%   浏览 {pv / 10000:.1f} 万", va="center", fontsize=8.5, color=INK2)
    ax.set_xlabel("购买次数 / 浏览次数（%）")
    ax.set_xlim(0, xmax * 1.6)
    style_axes(ax, grid="x")
    ax.set_title("浏览量前 20 的类目：转化率差异很大", loc="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, SAMPLE_NOTE + "；自上而下按浏览量从高到低", fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def fig_repurchase(dist, rep, out):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    total = dist["users"].sum()
    ax.bar(dist["buy_times"].astype(str), dist["users"], color=BLUE, width=0.65)
    for x, v in zip(dist["buy_times"].astype(str), dist["users"]):
        ax.text(x, v + total * 0.008, f"{v:,}\n({v / total:.0%})", ha="center", fontsize=9, color=INK2)
    ax.set_xlabel("9 天内购买次数")
    ax.set_ylim(0, dist["users"].max() * 1.2)
    style_axes(ax)
    rate = rep.iloc[0]["repeat_rate_pct"]
    ax.set_title(f"购买用户的购买次数分布：复购用户占 {rate:.1f}%", loc="left", fontsize=13, fontweight="bold")
    fig.text(0.01, 0.01, SAMPLE_NOTE, fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=160)
    plt.close(fig)


def build_all(fetch, out_dir=FIG_DIR):
    setup_style()
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)
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
    print("已生成:", build_all(make_fetch()))
