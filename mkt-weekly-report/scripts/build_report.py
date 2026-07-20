# -*- coding: utf-8 -*-
"""주간 마케팅 주요지표 보고서 PDF 빌더.

reads  <workspace>/ga4_data.json + <workspace>/ads_data.json
writes <outdir>/<주차>.md + charts/*.png + <주차>.pdf (make-pdf)

날짜창/주차 라벨은 실행일(또는 --date) 기준 자동 계산. SNS 조회수(유튜브·인스타)는
API로 못 얻는 수동 입력값이라 --yt-views / --ig-views 로 주간 반영(미입력 시 '미입력' 표기).
조코딩AX 사이트·이벤트·플랫폼 매핑은 상수로 내장(수집 스크립트와 동일 실측).
"""
import argparse
import base64
import datetime
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# 한글 폰트 자동 탐지 (macOS AppleGothic / Linux NanumGothic)
for _fam in ["AppleGothic", "NanumGothic", "Malgun Gothic"]:
    try:
        matplotlib.font_manager.findfont(_fam, fallback_to_default=False)
        plt.rcParams["font.family"] = _fam
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

DEF_ADS = os.path.expanduser("~/Desktop/dev/marketing/ads")
DEF_PDF_BIN = os.environ.get("MAKE_PDF_BIN", os.path.expanduser("~/.claude/skills/gstack/make-pdf/dist/pdf"))
BLUE, ORANGE, RED, GREEN, PURPLE, GRAY = "#2563eb", "#f59e0b", "#dc2626", "#16a34a", "#7c3aed", "#94a3b8"

# 소스 → 플랫폼 정규화 (조코딩AX 실측 소스 기준)
CONTEST = {"linkareer": "링커리어(+콘테스트코리아)", "ssgsag": "에스에스지생각", "allforyoung": "올포영",
           "everytime": "에브리타임", "campuspick": "캠퍼스픽", "allcon": "올콘", "thinkcontest": "씽굿",
           "incruit": "인크루트", "wikidocs": "위키독스"}


def platform(src, med=""):
    s = (src or "").lower(); m = (med or "").lower()
    if s == "google" and m == "cpc": return "구글 검색광고"
    if s == "google": return "구글 자연검색"
    if s in ("(direct)", "direct", ""): return "직접유입"
    if "youtube" in s: return "유튜브"
    if "instagram" in s or s == "ig": return "인스타그램"
    if s in ("contestkorea", "linkareer"): return "링커리어(+콘테스트코리아)"
    if s == "groupby": return "파트너(groupby)"
    if "primer" in s: return "프라이머(referral)"
    if "naver" in s: return "네이버"
    if "threads" in s: return "스레드"
    if "linkedin" in s: return "링크드인"
    if "github" in s: return "깃허브"
    if "bing" in s: return "Bing"
    if "chatgpt" in s: return "ChatGPT"
    if s in CONTEST and s != "linkareer": return f"공모전:{s}"
    if s in ("hackathon_landing",): return "해커톤랜딩(내부)"
    return src or "(기타)"


def main() -> None:
    ap = argparse.ArgumentParser(description="주간 마케팅 보고서 PDF 빌더")
    ap.add_argument("--ads-dir", default=DEF_ADS)
    ap.add_argument("--workspace", default=None, help="ga4_data.json/ads_data.json 위치 (기본 <ads-dir>/../_workspace)")
    ap.add_argument("--outdir", default=None, help="리포트 출력 폴더 (기본 <ads-dir>/reports/주간마케팅/<주차>)")
    ap.add_argument("--date", default=None, help="리포트 기준일 ISO (기본 오늘). 데이터 수집일과 맞출 것")
    ap.add_argument("--week", default=None, help="주차 라벨 (기본 자동: 'M월 N주차')")
    ap.add_argument("--title", default=None, help="PDF 제목 (기본 '조코딩AX 마케팅 주간보고 · <주차>')")
    ap.add_argument("--author", default="조코딩AX 마케팅")
    ap.add_argument("--yt-views", type=int, default=0, help="유튜브 쇼츠 총 조회수 (주간 수동 입력)")
    ap.add_argument("--ig-views", type=int, default=0, help="인스타 릴스 총 조회수 (주간 수동 입력)")
    ap.add_argument("--make-pdf-bin", default=DEF_PDF_BIN)
    args = ap.parse_args()

    ads_dir = os.path.abspath(os.path.expanduser(args.ads_dir))
    ws = os.path.abspath(os.path.expanduser(args.workspace or os.path.join(ads_dir, "..", "_workspace")))
    G = json.load(open(os.path.join(ws, "ga4_data.json")))
    A = json.load(open(os.path.join(ws, "ads_data.json")))

    run_date = datetime.date.fromisoformat(args.date) if args.date else datetime.date.today()
    yday = run_date - datetime.timedelta(days=1)
    s14 = run_date - datetime.timedelta(days=14)
    s7 = run_date - datetime.timedelta(days=7)
    PERIOD = f"{s14.isoformat()} ~ {yday.strftime('%m-%d')}"
    PERIOD7 = f"{s7.isoformat()} ~ {yday.strftime('%m-%d')}"
    week = args.week or f"{run_date.month}월 {(run_date.day - 1) // 7 + 1}주차"
    title = args.title or f"조코딩AX 마케팅 주간보고 · {week}"

    outdir = Path(os.path.expanduser(args.outdir)) if args.outdir else Path(ads_dir) / "reports" / "주간마케팅" / week
    CH = outdir / "charts"; CH.mkdir(parents=True, exist_ok=True)

    yt_views, ig_views = args.yt_views, args.ig_views
    sns_total = yt_views + ig_views
    sns_has = sns_total > 0

    def md(x): return f"{x:,}"

    def mmdd(s):
        s = s.replace("-", "")  # GA4=20260706 / Ads=2026-07-06 둘 다 처리
        return f"{s[4:6]}/{s[6:8]}"

    def man(v):
        # 만 단위 미만은 '천'으로 (예: 5,200 → 5.2천), 이상은 '만'으로 (48,000 → 4.8만)
        if v < 10000:
            return f"{v / 1000:.1f}천"
        return f"{v // 10000}.{(v % 10000) // 1000}만"

    # ---------------- 파생 집계 ----------------
    home_sess = sum(x["sessions"] for x in G["home_daily"])
    home_cta = sum(x["cta"] for x in G["home_daily"])
    hack_sess = sum(x["sessions"] for x in G["hack_daily"])
    hack_cta = sum(x["cta"] for x in G["hack_daily"])
    blog_sess = sum(x["sessions"] for x in G["blog_daily"])
    primer_sess = G["primer_sessions_14d"]; primer_sub = G["primer_form_submit_14d"]
    ad_cost_14 = sum(x["cost"] for x in A["daily_14d"])
    ad_click_14 = sum(x["clicks"] for x in A["daily_14d"])

    def agg_platform(rows, cta_key="cta"):
        d = defaultdict(lambda: {"s": 0, "cta": 0, "bw": 0.0})
        for r in rows:
            p = platform(r["source"], r.get("medium", ""))
            a = d[p]; a["s"] += r["sessions"]; a["cta"] += r[cta_key]; a["bw"] += r["bounce"] * r["sessions"]
        out = [{"platform": k, "sessions": v["s"], "cta": v["cta"],
                "bounce": round(v["bw"] / v["s"], 1) if v["s"] else 0} for k, v in d.items()]
        return sorted(out, key=lambda x: -x["sessions"])

    home_plat = agg_platform(G["home_source"])
    hack_plat = agg_platform(G["hack_source"])

    def gshare(plat, tot):
        return sum(x["sessions"] for x in plat if x["platform"].startswith("구글")) / tot * 100 if tot else 0
    home_g = gshare(home_plat, home_sess)

    # 해커톤 연동 UTM: source 단위 집계 + contestkorea→linkareer 병합
    utm = defaultdict(lambda: {"s": 0, "u": 0, "cta": 0, "bw": 0.0})
    for r in G["hack_utm"]:
        src = "linkareer" if r["source"] == "contestkorea" else r["source"]
        a = utm[src]; a["s"] += r["sessions"]; a["u"] += r["users"]; a["cta"] += r["cta"]; a["bw"] += r["bounce"] * r["sessions"]
    utm_rows = sorted([{"source": k, "sessions": v["s"], "users": v["u"], "cta": v["cta"],
                        "bounce": round(v["bw"] / v["s"], 1) if v["s"] else 0} for k, v in utm.items()],
                      key=lambda x: -x["sessions"])
    utm_tot = sum(r["sessions"] for r in utm_rows)

    contest_rows = [r for r in utm_rows if r["source"] in CONTEST]
    csum = sum(r["sessions"] for r in contest_rows)
    ccta = sum(r["cta"] for r in contest_rows)
    cbounce = sum(r["bounce"] * r["sessions"] for r in contest_rows) / csum if csum else 0

    # SNS 랜딩 유입 (데이터 기반)
    yt_sess = next((r["sessions"] for r in utm_rows if r["source"] == "youtube.com"), 0)
    ig_sess = (next((r["sessions"] for r in utm_rows if r["source"] == "l.instagram.com"), 0)
               + next((r["sessions"] for r in utm_rows if r["source"] == "ig"), 0))

    # ---------------- 차트 ----------------
    def save(fig, name):
        fig.tight_layout(); fig.savefig(CH / name, dpi=115, bbox_inches="tight"); plt.close(fig)

    d = G["home_daily"]; labels = [mmdd(x["date"]) for x in d]
    fig, ax1 = plt.subplots(figsize=(6.6, 3.4))
    ax1.bar(labels, [x["sessions"] for x in d], color=BLUE, alpha=.8)
    ax1.set_ylabel("세션", color=BLUE); ax1.tick_params(axis="x", rotation=45, labelsize=8)
    ax2 = ax1.twinx(); ax2.plot(labels, [x["cta"] for x in d], color=ORANGE, marker="o", lw=2)
    ax2.set_ylabel("CTA클릭(cta_click)", color=ORANGE)
    ax1.set_title("jocodingax.ai 일별 세션·CTA클릭 (최근 14일)", fontsize=12, fontweight="bold")
    save(fig, "1_home.png")

    d = G["hack_daily"]; labels = [mmdd(x["date"]) for x in d]
    fig, ax1 = plt.subplots(figsize=(6.6, 3.4))
    ax1.bar(labels, [x["sessions"] for x in d], color=PURPLE, alpha=.8)
    ax1.set_ylabel("세션", color=PURPLE); ax1.tick_params(axis="x", rotation=45, labelsize=8)
    ax2 = ax1.twinx(); ax2.plot(labels, [x["cta"] for x in d], color=GREEN, marker="o", lw=2)
    ax2.set_ylabel("프라이머 이동(cta_apply_click)", color=GREEN)
    ax1.set_title("hackathon.jocodingax.ai 일별 세션·프라이머 이동 (최근 14일)", fontsize=12, fontweight="bold")
    save(fig, "2_hack.png")

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    steps = ["해커톤 랜딩\n세션", "프라이머 이동\n(cta_apply_click)", "프라이머 신청폼\n제출(form_submit)*"]
    vals = [hack_sess, hack_cta, primer_sub]; colors = [PURPLE, GREEN, BLUE]
    bars = ax.bar(steps, vals, color=colors, alpha=.85)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), md(v), ha="center", va="bottom", fontsize=11, fontweight="bold")
    if hack_sess:
        ax.annotate(f"↓ 이동율 {hack_cta / hack_sess * 100:.0f}%", xy=(0.5, (hack_sess + hack_cta) / 2),
                    ha="center", va="center", color="#111827", fontsize=11, fontweight="bold")
    ax.set_ylabel("건수"); ax.set_ylim(0, max(vals) * 1.18 if max(vals) else 1)
    ax.set_title("해커톤 신청 퍼널 (최근 14일)", fontsize=12, fontweight="bold")
    save(fig, "3_funnel.png")

    top = utm_rows[:10][::-1]
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    ax.barh([r["source"] for r in top], [r["sessions"] for r in top], color=PURPLE, alpha=.8)
    for i, r in enumerate(top):
        ax.text(r["sessions"], i, f' {md(r["sessions"])}', va="center", fontsize=8)
    ax.set_xlabel("세션"); ax.set_title("해커톤 랜딩 유입 소스 TOP10 (최근 14일)", fontsize=12, fontweight="bold")
    save(fig, "4_hacksrc.png")

    d = A["daily_7d"]; labels = [mmdd(x["date"]) for x in d]
    fig, ax1 = plt.subplots(figsize=(6.6, 3.4))
    ax1.bar(labels, [x["cost"] for x in d], color=BLUE, alpha=.8)
    ax1.set_ylabel("지출(원)", color=BLUE); ax1.tick_params(axis="x", rotation=45, labelsize=8)
    ax2 = ax1.twinx(); ax2.plot(labels, [x["clicks"] for x in d], color=ORANGE, marker="o", lw=2)
    ax2.set_ylabel("클릭", color=ORANGE)
    ax1.set_title("구글 광고 일별 지출·클릭 (최근 7일)", fontsize=12, fontweight="bold")
    save(fig, "5_adspend.png")

    top = home_plat[:6]; other = sum(x["sessions"] for x in home_plat[6:])
    vals = [x["sessions"] for x in top] + ([other] if other else [])
    names = [x["platform"] for x in top] + (["기타"] if other else [])
    fig, ax = plt.subplots(figsize=(6.6, 3.8))
    ax.pie(vals, labels=[f"{n}\n{md(v)}" for n, v in zip(names, vals)], autopct="%1.0f%%",
           startangle=90, wedgeprops=dict(width=0.42), textprops={"fontsize": 8})
    ax.set_title("jocodingax.ai 유입 소스 비율 (최근 14일)", fontsize=12, fontweight="bold")
    save(fig, "6_homesrc.png")

    # ---------------- 표 빌더 ----------------
    def plat_table(rows, cta_label, tot):
        top = rows[:8]; oth = rows[8:]
        lines = [f"| 플랫폼 | 세션 | 비율 | {cta_label} | {cta_label[:2]}율 | 이탈률 |", "|---|--:|--:|--:|--:|--:|"]
        for r in top:
            lines.append(f'| {r["platform"]} | {md(r["sessions"])} | {r["sessions"] / tot * 100:.1f}% | '
                         f'{md(r["cta"])} | {r["cta"] / r["sessions"] * 100:.0f}% | {r["bounce"]:.0f}% |')
        if oth:
            os_, oc = sum(x["sessions"] for x in oth), sum(x["cta"] for x in oth)
            lines.append(f'| 기타({len(oth)}개) | {md(os_)} | {os_ / tot * 100:.1f}% | {md(oc)} | {oc / os_ * 100:.0f}% | — |')
        lines.append(f'| **합계** | **{md(tot)}** | 100% | **{md(sum(r["cta"] for r in rows))}** | '
                     f'**{sum(r["cta"] for r in rows) / tot * 100:.0f}%** | — |')
        return "\n".join(lines)

    home_src_tbl = plat_table(home_plat, "CTA클릭", home_sess)
    hack_src_tbl = plat_table(hack_plat, "프라이머이동", hack_sess)

    # 홈 유입경로(채널그룹) 표 — 표준 GA4 채널 기준
    home_ch = G.get("home_channel", [])
    home_ch_tot = sum(r["sessions"] for r in home_ch)
    ch_lines = ["| 유입경로(채널그룹) | 세션 | 비율 | 이탈률 | CTA클릭 |", "|---|--:|--:|--:|--:|"]
    for r in home_ch:
        ch_lines.append(f'| {r["channel"]} | {md(r["sessions"])} | {r["sessions"] / home_ch_tot * 100:.1f}% | {r["bounce"]:.0f}% | {md(r["cta"])} |')
    if home_ch:
        ch_lines.append(f'| **합계** | **{md(home_ch_tot)}** | 100% | — | **{md(sum(r["cta"] for r in home_ch))}** |')
    home_ch_tbl = "\n".join(ch_lines) if home_ch else "_(채널그룹 데이터 없음 — collect_ga4 재실행 필요)_"

    utm_lines = ["| 소스(UTM) | 세션 | 사용자 | 비율 | 이탈률 | 프라이머이동 | 이동율 |", "|---|--:|--:|--:|--:|--:|--:|"]
    for r in utm_rows:
        if r["sessions"] < 15: continue
        utm_lines.append(f'| {r["source"]} | {md(r["sessions"])} | {md(r["users"])} | {r["sessions"] / utm_tot * 100:.1f}% | '
                         f'{r["bounce"]:.0f}% | {md(r["cta"])} | {r["cta"] / r["sessions"] * 100:.0f}% |')
    tot_cta = sum(r["cta"] for r in utm_rows)
    utm_lines.append(f'| **합계(전체)** | **{md(utm_tot)}** | — | 100% | — | **{md(tot_cta)}** | **{tot_cta / utm_tot * 100:.0f}%** |')
    utm_tbl = "\n".join(utm_lines)

    c_lines = ["| 공모전 플랫폼 | 세션 | 이탈률 | 프라이머이동 | 이동율 |", "|---|--:|--:|--:|--:|"]
    for r in contest_rows:
        c_lines.append(f'| {CONTEST[r["source"]]} | {md(r["sessions"])} | {r["bounce"]:.0f}% | {md(r["cta"])} | {r["cta"] / r["sessions"] * 100:.0f}% |')
    c_lines.append(f'| **합계** | **{md(csum)}** | — | **{md(ccta)}** | **{ccta / csum * 100:.0f}%** |' if csum else '| **합계** | 0 | — | 0 | — |')
    contest_tbl = "\n".join(c_lines)

    kw_lines = ["| 키워드 | 캠페인 | 노출 | 클릭 | CTR | 비용 | CPC | QS |", "|---|---|--:|--:|--:|--:|--:|--:|"]
    for k in A["keywords_14d"][:12]:
        camp = "인재전쟁" if "인재" in k["campaign"] else ("기업AI교육" if "교육" in k["campaign"] else k["campaign"][:8])
        kw_lines.append(f'| {k["kw"]} | {camp} | {md(k["impr"])} | {md(k["clicks"])} | {k["ctr"]}% | '
                        f'{md(k["cost"])} | {md(k["cpc"])} | {k["qs"] or "—"} |')
    kw_tbl = "\n".join(kw_lines)

    camp_lines = ["| 캠페인 | 상태 | 비용 | 클릭 | CTR | CPC | 노출점유율 |", "|---|---|--:|--:|--:|--:|--:|"]
    for c in A["campaigns_14d"]:
        camp_lines.append(f'| {c["name"]} | {c["status"]} | {md(c["cost"])} | {md(c["clicks"])} | {c["ctr"]}% | '
                          f'{md(c["cpc"])} | {c["is"] if c["is"] is not None else "—"}% |')
    camp_tbl = "\n".join(camp_lines)

    sp_lines = ["| 일자 | 지출(원) | 클릭 | 노출 | CPC(클릭당) |", "|---|--:|--:|--:|--:|"]
    tc = tk = ti = 0
    for x in A["daily_7d"]:
        cpc = round(x["cost"] / x["clicks"]) if x["clicks"] else 0
        sp_lines.append(f'| {mmdd(x["date"])} | {md(x["cost"])} | {md(x["clicks"])} | {md(x["impr"])} | {md(cpc)} |')
        tc += x["cost"]; tk += x["clicks"]; ti += x["impr"]
    sp_lines.append(f'| **합계** | **{md(tc)}** | **{md(tk)}** | **{md(ti)}** | **{md(round(tc / tk) if tk else 0)}** |')
    spend_tbl = "\n".join(sp_lines)

    lp_all = [x for x in G["home_cpc_landing"] if x["sessions"] >= 5]
    lp_lines = ["| 랜딩 페이지 | 세션 | 이탈률 |", "|---|--:|--:|"]
    for x in lp_all:
        lp_lines.append(f'| {x["page"]} | {md(x["sessions"])} | {x["bounce"]:.0f}% |')
    lp_tbl = "\n".join(lp_lines)
    g_cpc = next((x for x in G["home_google"] if x["medium"] == "cpc"), {"sessions": 0, "bounce": 0})
    g_org = next((x for x in G["home_google"] if x["medium"] == "organic"), {"sessions": 0, "bounce": 0})

    bp_lines = ["| 페이지 | 조회수 | 세션 | 이탈률 |", "|---|--:|--:|--:|"]
    for x in G["blog_top_pages"][:8]:
        bp_lines.append(f'| {x["path"]} | {md(x["views"])} | {md(x["sessions"])} | {x["bounce"]:.0f}% |')
    blog_tbl = "\n".join(bp_lines)
    bc_lines = ["| 채널 | 세션 |", "|---|--:|"]
    for x in G["blog_channels"]:
        if x["sessions"] < 1: continue
        bc_lines.append(f'| {x["channel"]} | {md(x["sessions"])} |')
    blog_ch_tbl = "\n".join(bc_lines)
    blog_ref = sum(r["sessions"] for r in G.get("home_blog_referral", []))
    top_ch = G["blog_channels"][0]["channel"] if G["blog_channels"] else "—"

    # ---------------- 데이터 기반 코멘트 ----------------
    sns_metric = f"**{md(sns_total)}**" if sns_has else "(미입력)"
    sns_note = f"유튜브 {man(yt_views)} · 인스타 {man(ig_views)}" if sns_has else "이번 주 SNS 조회수 미입력"
    if sns_has:
        sns_line = (f"- **SNS 조회수: 유튜브 쇼츠 {man(yt_views)} + 인스타 릴스 {man(ig_views)} = 총 {md(sns_total)}회.** "
                    f"이 도달이 유튜브({md(yt_sess)}세션)·인스타({md(ig_sess)}세션) 랜딩 유입으로 전환됨.")
        hl2 = (f"2. **SNS 도달 {sns_total // 10000}만+** (유튜브 쇼츠 {man(yt_views)}·인스타 릴스 {man(ig_views)}) — 상단 퍼널을 강하게 채우는 중.")
    else:
        sns_line = (f"- SNS 조회수는 이번 주 미입력(다음 실행 시 `--yt-views/--ig-views`로 반영). "
                    f"현재 유튜브·인스타 랜딩 유입은 각 {md(yt_sess)}·{md(ig_sess)}세션.")
        hl2 = "2. **SNS 도달** — 유튜브 쇼츠·인스타 릴스 조회수 이번 주 미입력(다음 실행 시 반영)."

    if csum:
        contest_note = (f"- 공모전 플랫폼은 이탈률이 낮고(가중 평균 {cbounce:.0f}%) 프라이머 이동율이 높음(평균 {ccta / csum * 100:.0f}%) — 유입 질이 우수한 그룹."
                        + (f" 특히 **{CONTEST[contest_rows[0]['source']]}**가 규모·효율 선두({md(contest_rows[0]['cta'])}건 이동)." if contest_rows else ""))
        hl3 = f"3. **공모전·인스타 = 고효율 채널** — 공모전 이탈률 가중 {cbounce:.0f}%·프라이머 이동율 평균 {ccta / csum * 100:.0f}%로 유입 질 최상위."
    else:
        contest_note = "- 이번 기간 공모전 플랫폼 유입은 소량."
        hl3 = "3. **채널 품질** — 공모전·인스타 유입이 이탈률 낮고 이동율 높은 편."

    if lp_all:
        top_lp = lp_all[0]
        bmin = min(lp_all, key=lambda x: x["bounce"]); bmax = max(lp_all, key=lambda x: x["bounce"])
        lp_note = (f"- 광고 트래픽은 주로 상위 랜딩(`{top_lp['page']}`, {md(top_lp['sessions'])}세션·이탈률 {top_lp['bounce']:.0f}%)으로 인입. "
                   f"페이지별 이탈률 편차가 큼({bmin['bounce']:.0f}~{bmax['bounce']:.0f}%) — 이탈률 높은 페이지는 랜딩 최적화 여지.")
    else:
        lp_note = "- google/cpc 랜딩 데이터 소량."

    blog_note = (f"- 유입은 {top_ch} 중심. 상위 콘텐츠는 도입사례·기업교육 글 위주로 세일즈·채용 신뢰 콘텐츠로 기능 중. "
                 f"(본사이트로의 블로그 리퍼럴은 {md(blog_ref)}세션)")

    hack_home_ratio = f"{hack_sess / home_sess:.1f}배" if home_sess else "—"

    # ---------------- 마크다운 ----------------
    report = f"""# {title.split('·')[0].strip()} · {week}

**기간** {PERIOD} (최근 14일) · **광고 지출표** {PERIOD7} (최근 7일)
**대상** jocodingax.ai(홈) · hackathon.jocodingax.ai(해커톤 랜딩) · blog.jocodingax.ai · 구글 검색광고
**작성** {args.author} · GA4 + Google Ads 실측

---

## 한눈에 보기 (핵심 지표)

| 지표 | 값 | 비고 |
|---|--:|---|
| 해커톤 랜딩 세션 | **{md(hack_sess)}** | 프라이머 이동 {md(hack_cta)}건 (**{hack_cta / hack_sess * 100:.0f}%**) |
| 프라이머 신청폼 제출 | **{md(primer_sub)}** | hack.primer.kr 도착 {md(primer_sess)}세션 |
| 홈(jocodingax.ai) 세션 | **{md(home_sess)}** | CTA클릭 {md(home_cta)}건 ({home_cta / home_sess * 100:.0f}%) |
| SNS 조회수(쇼츠·릴스) | {sns_metric} | {sns_note} |
| 구글 광고 지출(14일) | **{md(ad_cost_14)}원** | 클릭 {md(ad_click_14)} · CPC {md(round(ad_cost_14 / ad_click_14)) if ad_click_14 else 0}원 |
| 블로그 세션 | {md(blog_sess)} | 상위글 도입사례/기업교육 |

> **총평** — 해커톤 랜딩이 이번 2주 트래픽의 중심(홈 대비 약 {hack_home_ratio}). 랜딩 방문자의
> **{hack_cta / hack_sess * 100:.0f}%가 프라이머 신청 페이지로 이동**했고, 프라이머 신청폼 제출은 **{md(primer_sub)}건**.
> 유입은 구글 검색광고·파트너(groupby)·유튜브·공모전 플랫폼이 고르게 견인했으며, 공모전·인스타 유입은
> 이탈률이 낮고 이동율이 높은 **고품질 채널**로 확인됨.

---

# Part 1. 사이트 트래픽 개요

## 1.1 jocodingax.ai — 일별 세션·CTA클릭

![홈 일별](charts/1_home.png)

- 14일 합계 **세션 {md(home_sess)} · CTA클릭 {md(home_cta)}건**(전환율 {home_cta / home_sess * 100:.1f}%). CTA=`cta_click`(주요 전환 버튼).
- 유입의 약 {home_g:.0f}%가 **구글**(검색광고+자연 합산). 상세 페이지별 이탈률은 2.6 참고.

## 1.2 hackathon.jocodingax.ai — 일별 세션·프라이머 이동

![해커톤 일별](charts/2_hack.png)

- 14일 합계 **세션 {md(hack_sess)} · 프라이머 이동 {md(hack_cta)}건**(이동율 **{hack_cta / hack_sess * 100:.0f}%**).
- "프라이머 이동" = `cta_apply_click`(목적지 `hack.primer.kr` 실측 확인). 신청 CTA 클릭 = 프라이머 신청 페이지 진입.

## 1.3 유입 소스(플랫폼)별 성과 — 세션·CTA·비율·이탈률

**jocodingax.ai (홈)**

{home_src_tbl}

![홈 소스](charts/6_homesrc.png)

**jocodingax.ai 유입경로(채널그룹)** — 표준 GA4 채널 기준

{home_ch_tbl}

**hackathon.jocodingax.ai (해커톤 랜딩)**

{hack_src_tbl}

> 홈은 구글 의존도가 높고(≈{home_g:.0f}%), 해커톤은 광고·파트너·유튜브·공모전으로 **분산**되어 채널 리스크가 낮음.

---

# Part 2. 캠페인·채널 성과

## 2.1 해커톤 신청 퍼널 & SNS 성과

![퍼널](charts/3_funnel.png)

- **랜딩 {md(hack_sess)} → 프라이머 이동 {md(hack_cta)}({hack_cta / hack_sess * 100:.0f}%) → 프라이머 신청폼 {md(primer_sub)}건.**
  (*프라이머 신청폼은 hack.primer.kr 전체 기준 — 우리 랜딩 외 직접유입 포함*)
{sns_line}

## 2.2 해커톤 랜딩 연동 UTM 전체 분석 (이탈률·프라이머이동 포함)

> 소스(UTM)별 집계 · **콘테스트코리아는 링커리어에 합산**(사용자 요청) · 세션 15건 이상.

{utm_tbl}

![해커톤 소스](charts/4_hacksrc.png)

## 2.3 공모전 플랫폼 UTM 성과 (콘테스트코리아→링커리어 합산)

{contest_tbl}

{contest_note}

## 2.4 구글 키워드 광고 성과 (최근 14일)

**캠페인 요약**

{camp_tbl}

**키워드 TOP (비용순)**

{kw_tbl}

- 브랜드 키워드(ax인재전쟁·조코딩 해커톤)는 CTR·QS가 높아 효율적. 일반 키워드는 QS·CPC 모니터링 대상.

## 2.5 최근 7일 일자별 지출 (합계·클릭당 CPC 포함)

{spend_tbl}

![일별 지출](charts/5_adspend.png)

## 2.6 구글 검색광고 → jocodingax.ai 페이지별 이탈률 (최근 14일)

> google / cpc 세션 기준. 전체 google/cpc **{md(g_cpc['sessions'])}세션 · 이탈률 {g_cpc['bounce']:.0f}%**
> (참고: google 자연검색 {md(g_org['sessions'])}세션 · 이탈률 {g_org['bounce']:.0f}%).

{lp_tbl}

{lp_note}

## 2.7 블로그(blog.jocodingax.ai) 유입 성과

블로그 14일 **세션 {md(blog_sess)}**. 채널·상위 콘텐츠:

{blog_ch_tbl}

**상위 페이지**

{blog_tbl}

{blog_note}

---

## 전사 공유용 하이라이트

1. **해커톤이 이번 2주 마케팅의 엔진** — 랜딩 {md(hack_sess)}세션, 방문자 {hack_cta / hack_sess * 100:.0f}%가 프라이머로 이동, **신청폼 {md(primer_sub)}건**.
{hl2}
{hl3}
4. **채널 분산 우수** — 광고·파트너·유튜브·공모전이 고르게 기여, 단일 채널 의존 리스크 낮음.
5. **광고 효율 안정** — 14일 {md(ad_cost_14)}원 지출, CPC {md(round(ad_cost_14 / ad_click_14)) if ad_click_14 else 0}원, 브랜드 키워드 중심 고QS.
"""

    md_path = outdir / f"주간마케팅-보고-{run_date.isoformat()}.md"
    md_path.write_text(report, encoding="utf-8")

    # base64 임베드 후 PDF
    def embed(m):
        b = base64.b64encode((outdir / m.group(2)).read_bytes()).decode()
        return f"![{m.group(1)}](data:image/png;base64,{b})"
    b64 = re.sub(r"!\[([^\]]*)\]\((charts/[^)]+)\)", embed, report)
    tmp = outdir / ".b64.md"; tmp.write_text(b64, encoding="utf-8")

    pdf = outdir / f"조코딩AX-마케팅-주간보고-{run_date.isoformat()}-{week.replace(' ', '')}.pdf"
    binp = os.path.expanduser(args.make_pdf_bin)
    if os.path.exists(binp):
        subprocess.run([binp, "generate", "--cover", "--toc", "--no-confidential",
                        "--title", title, "--author", args.author,
                        "--date", run_date.isoformat(), str(tmp), str(pdf)], check=True)
        tmp.unlink(missing_ok=True)
        print(f"PDF: {pdf}")
    else:
        print(f"make-pdf 바이너리 없음({binp}) — MD만 생성: {md_path}")


if __name__ == "__main__":
    main()
