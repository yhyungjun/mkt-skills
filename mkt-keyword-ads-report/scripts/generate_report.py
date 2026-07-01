#!/usr/bin/env python3
"""키워드 광고 성과 리포트 생성기 — Google Ads + GA4 실데이터 → 차트 임베드 PDF.

수집(Ads 키워드 성과/일별/노출점유율/품질 + GA4 신청퍼널) → matplotlib 차트 4종 →
마크다운 리포트 → 차트 base64 인라인 임베드 → make-pdf 로 PDF.

의존성: google-ads, matplotlib, PyYAML (+ make-pdf 바이너리)
  pip install "google-ads>=24,<25" matplotlib PyYAML

사용:
  python generate_report.py \
    --campaign "AX 인재전쟁" --cid 8834896313 --ga4 542898562 \
    --yaml /path/to/google-ads.yaml --preset this_week \
    --outdir "/path/to/out" --title "AX 인재전쟁 — 주간 키워드 리포트"

프리셋: this_week(월~오늘) | last_7_days | last_14_days  또는 --start/--end (YYYY-MM-DD).
WoW 비교는 직전 동일길이 기간을 자동 계산.
전환(Ads conversion)은 기본 제외, 신청은 GA4 cta_apply_click(--apply-event 로 변경) 기준.
"""
import argparse, base64, datetime, json, os, re, subprocess, sys, urllib.parse, urllib.request, warnings
from pathlib import Path
warnings.filterwarnings("ignore")


# ---------- 기간 계산 ----------
def resolve_period(preset, start, end):
    today = datetime.date.today()
    if start and end:
        return start, end
    if preset == "last_7_days":
        return (today - datetime.timedelta(days=6)).isoformat(), today.isoformat()
    if preset == "last_14_days":
        return (today - datetime.timedelta(days=13)).isoformat(), today.isoformat()
    # this_week (기본): 이번 주 월요일 ~ 오늘
    mon = today - datetime.timedelta(days=today.weekday())
    return mon.isoformat(), today.isoformat()


def prev_period(s, e):
    sd, ed = datetime.date.fromisoformat(s), datetime.date.fromisoformat(e)
    length = (ed - sd).days + 1
    pe = sd - datetime.timedelta(days=1)
    ps = pe - datetime.timedelta(days=length - 1)
    return ps.isoformat(), pe.isoformat()


# ---------- Google Ads ----------
def ads_client(yaml_path):
    from google.ads.googleads.client import GoogleAdsClient
    return GoogleAdsClient.load_from_storage(yaml_path)


def ads_campaign(ga, cid, camp, s, e):
    q = f"""SELECT campaign.serving_status, campaign_budget.amount_micros,
        metrics.impressions, metrics.clicks, metrics.ctr, metrics.cost_micros, metrics.average_cpc,
        metrics.search_impression_share, metrics.search_budget_lost_impression_share,
        metrics.search_rank_lost_impression_share
        FROM campaign WHERE campaign.name='{camp}' AND segments.date BETWEEN '{s}' AND '{e}'"""
    for r in ga.search(customer_id=cid, query=q):
        m = r.metrics
        return dict(serving=r.campaign.serving_status.name,
                    budget=r.campaign_budget.amount_micros / 1e6,
                    imp=m.impressions, clk=m.clicks, ctr=m.ctr, cost=m.cost_micros / 1e6,
                    cpc=m.average_cpc / 1e6, sis=m.search_impression_share,
                    blost=m.search_budget_lost_impression_share, rlost=m.search_rank_lost_impression_share)
    return None


def ads_daily(ga, cid, camp, s, e):
    q = f"""SELECT segments.date, metrics.impressions, metrics.clicks, metrics.ctr,
        metrics.cost_micros, metrics.average_cpc,
        metrics.search_budget_lost_impression_share, metrics.search_rank_lost_impression_share
        FROM campaign WHERE campaign.name='{camp}' AND segments.date BETWEEN '{s}' AND '{e}'
        ORDER BY segments.date"""
    out = []
    for r in ga.search(customer_id=cid, query=q):
        m = r.metrics
        out.append(dict(date=r.segments.date, imp=m.impressions, clk=m.clicks, ctr=m.ctr,
                        cost=m.cost_micros / 1e6, cpc=m.average_cpc / 1e6,
                        blost=m.search_budget_lost_impression_share, rlost=m.search_rank_lost_impression_share))
    return out


def ads_keywords(ga, cid, camp, s, e):
    q = f"""SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type,
        ad_group_criterion.status, ad_group_criterion.quality_info.quality_score,
        metrics.impressions, metrics.clicks, metrics.ctr, metrics.cost_micros, metrics.average_cpc
        FROM keyword_view WHERE campaign.name='{camp}' AND ad_group_criterion.status='ENABLED'
        AND segments.date BETWEEN '{s}' AND '{e}' ORDER BY metrics.cost_micros DESC"""
    out = []
    for r in ga.search(customer_id=cid, query=q):
        c, m = r.ad_group_criterion, r.metrics
        out.append(dict(kw=c.keyword.text, match=c.keyword.match_type.name,
                        quality=c.quality_info.quality_score or 0,
                        imp=m.impressions, clk=m.clicks, ctr=m.ctr,
                        cost=m.cost_micros / 1e6, cpc=m.average_cpc / 1e6))
    return out


# ---------- GA4 ----------
def ga4_token(cfg):
    data = urllib.parse.urlencode({
        "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
        "refresh_token": cfg["refresh_token"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=data)))["access_token"]


def ga4_keyword_metric(token, pid, s, e, metric, event=None):
    exprs = [{"filter": {"fieldName": "sessionSourceMedium", "stringFilter": {"value": "google / cpc"}}}]
    if event:
        exprs.append({"filter": {"fieldName": "eventName", "stringFilter": {"value": event}}})
    body = {"dateRanges": [{"startDate": s, "endDate": e}],
            "dimensions": [{"name": "sessionGoogleAdsKeyword"}], "metrics": [{"name": metric}],
            "dimensionFilter": {"andGroup": {"expressions": exprs}}, "limit": 200}
    r = json.load(urllib.request.urlopen(urllib.request.Request(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{pid}:runReport",
        data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})))
    return {row["dimensionValues"][0]["value"].lower(): float(row["metricValues"][0]["value"])
            for row in r.get("rows", [])}


# ---------- 효율 등급 (휴리스틱) ----------
def grade(cpa, ctr, best_cpa):
    """신청클릭당 비용 기준 등급 + CTR 보정. best_cpa=최저 신청단가."""
    if not cpa or cpa <= 0:
        return "C"
    ratio = cpa / best_cpa if best_cpa else 99
    if ratio <= 1.5 or ctr >= 0.35:
        return "S"
    if ratio <= 3.0 or ctr >= 0.20:
        return "A"
    if ratio <= 4.5:
        return "B"
    return "C"


GRADE_ICON = {"S": "🟢", "A": "🟢", "B": "🟡", "C": "🔴"}


# ---------- 차트 ----------
def korean_font():
    from matplotlib import font_manager
    for p in ["/System/Library/Fonts/Supplemental/AppleGothic.ttf",
              "/System/Library/Fonts/AppleSDGothicNeo.ttc",
              "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]:
        if os.path.exists(p):
            font_manager.fontManager.addfont(p)
            return font_manager.FontProperties(fname=p).get_name()
    return None


def make_charts(data, outdir):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import rcParams
    import matplotlib.pyplot as plt
    fam = korean_font()
    if fam:
        rcParams["font.family"] = fam
    rcParams["axes.unicode_minus"] = False
    rcParams["figure.dpi"] = 150
    BLUE, GRAY, GREEN, RED, AMBER, SLATE = "#2563eb", "#94a3b8", "#16a34a", "#dc2626", "#f59e0b", "#334155"
    cdir = Path(outdir) / "charts"
    cdir.mkdir(parents=True, exist_ok=True)

    # 1. 일별 비용 + 클릭
    d = data["daily"]
    days = [x["date"][5:].replace("-", "/") for x in d]
    cost = [round(x["cost"]) for x in d]
    clk = [x["clk"] for x in d]
    fig, ax1 = plt.subplots(figsize=(7, 3.4))
    ax1.bar(days, cost, color=BLUE, alpha=.85, width=.55)
    ax1.set_ylabel("비용 (원)", color=BLUE); ax1.tick_params(axis="y", labelcolor=BLUE)
    ax1.set_ylim(0, max(cost) * 1.25 if cost else 1)
    for i, v in enumerate(cost):
        ax1.text(i, v + max(cost) * .02, f"{v:,}", ha="center", fontsize=8, color=SLATE)
    ax2 = ax1.twinx()
    ax2.plot(days, clk, color=RED, marker="o", lw=2)
    ax2.set_ylabel("클릭", color=RED); ax2.tick_params(axis="y", labelcolor=RED)
    ax2.set_ylim(0, max(clk) * 1.3 if clk else 1)
    for i, v in enumerate(clk):
        ax2.text(i, v + max(clk) * .04, f"{v}", ha="center", fontsize=8, color=RED)
    ax1.set_title("① 일별 비용·클릭 추이", fontsize=11, weight="bold")
    fig.tight_layout(); fig.savefig(cdir / "1_daily.png", bbox_inches="tight"); plt.close()

    # 2. 키워드별 비용 & CTR
    kws = data["keywords"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    y = range(len(kws))
    cols = [GREEN if k["ctr"] >= .3 else (RED if k["ctr"] < .06 else AMBER) for k in kws]
    ax.barh(y, [k["cost"] for k in kws], color=cols, alpha=.85)
    ax.set_yticks(list(y)); ax.set_yticklabels([k["kw"] for k in kws]); ax.invert_yaxis()
    ax.set_xlabel("비용 (원)")
    mx = max(k["cost"] for k in kws) if kws else 1
    for i, k in enumerate(kws):
        ax.text(k["cost"] + mx * .015, i, f"{round(k['cost']):,}원 · CTR {k['ctr']*100:.1f}%",
                va="center", fontsize=8.5, color=SLATE)
    ax.set_xlim(0, mx * 1.55)
    ax.set_title("② 키워드별 비용 & CTR", fontsize=11, weight="bold")
    fig.tight_layout(); fig.savefig(cdir / "2_kw_cost_ctr.png", bbox_inches="tight"); plt.close()

    # 3. 신청클릭당 비용 (효율)
    eff = [k for k in kws if k.get("cpa")]
    eff = sorted(eff, key=lambda k: k["cpa"])
    if eff:
        fig, ax = plt.subplots(figsize=(7, 3.4))
        y = range(len(eff))
        cols = [GRADE_ICON_COLOR(k["grade"]) for k in eff]
        ax.barh(y, [k["cpa"] for k in eff], color=cols, alpha=.85)
        ax.set_yticks(list(y)); ax.set_yticklabels([k["kw"] for k in eff]); ax.invert_yaxis()
        ax.set_xlabel("신청클릭당 비용 (원) — 낮을수록 효율적")
        mx = max(k["cpa"] for k in eff)
        for i, k in enumerate(eff):
            ax.text(k["cpa"] + mx * .015, i, f"{round(k['cpa']):,}원", va="center", fontsize=9, color=SLATE)
        ax.set_xlim(0, mx * 1.25)
        ax.set_title("③ 키워드별 신청클릭당 비용 (효율 순위)", fontsize=11, weight="bold")
        fig.tight_layout(); fig.savefig(cdir / "3_cost_per_apply.png", bbox_inches="tight"); plt.close()

    # 4. 노출점유율 병목 WoW
    cur, prev = data["campaign"], data.get("campaign_prev")
    if prev:
        labels = ["지난 기간", "이번 기간"]
        sis = [prev["sis"] * 100, cur["sis"] * 100]
        bud = [prev["blost"] * 100, cur["blost"] * 100]
        rnk = [prev["rlost"] * 100, cur["rlost"] * 100]
        fig, ax = plt.subplots(figsize=(7, 3.0))
        ax.barh(labels, sis, color=GREEN, label="획득(검색 IS)")
        ax.barh(labels, bud, left=sis, color=AMBER, label="예산손실")
        ax.barh(labels, rnk, left=[sis[i] + bud[i] for i in range(2)], color=RED, label="순위손실")
        for i in range(2):
            ax.text(sis[i] / 2, i, f"{sis[i]:.0f}%", ha="center", va="center", color="white", fontsize=9, weight="bold")
            ax.text(sis[i] + bud[i] / 2, i, f"{bud[i]:.0f}%", ha="center", va="center", color="white", fontsize=8.5)
            ax.text(sis[i] + bud[i] + rnk[i] / 2, i, f"{rnk[i]:.0f}%", ha="center", va="center", color="white", fontsize=9, weight="bold")
        ax.set_xlim(0, 100); ax.set_xlabel("노출점유율 (%)")
        ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.42), ncol=3, frameon=False, fontsize=9)
        ax.set_title("④ 노출점유율 병목 변화 (지난 → 이번)", fontsize=11, weight="bold")
        fig.tight_layout(); fig.savefig(cdir / "4_is_wow.png", bbox_inches="tight"); plt.close()


def GRADE_ICON_COLOR(g):
    return {"S": "#16a34a", "A": "#16a34a", "B": "#f59e0b", "C": "#dc2626"}[g]


# ---------- 마크다운 ----------
def pct(x):
    return f"{x*100:.1f}%" if x else "-"


def build_md(data, args):
    c = data["campaign"]; p = data.get("campaign_prev")
    s, e = data["period"]
    lines = []
    A = lines.append
    A(f"# {args.campaign} — 키워드 광고 성과 리포트\n")
    A("| 항목 | 내용 |")
    A("|---|---|")
    A(f"| 캠페인 | {args.campaign} |")
    A(f"| 광고계정 | {args.cid} |")
    A(f"| 데이터 기간 | {s} ~ {e} |")
    A(f"| 작성일 | {datetime.date.today().isoformat()} |")
    A(f"| 상태 | {c['serving']} · 일예산 {c['budget']:,.0f}원 |\n")
    A("---\n")

    A("## 1. 요약\n")
    A(f"- 노출 **{c['imp']:,}** · 클릭 **{c['clk']:,}** · CTR **{pct(c['ctr'])}** · 비용 **{c['cost']:,.0f}원** · 평균 CPC **{c['cpc']:,.0f}원**.")
    if data["keywords"]:
        top = max(data["keywords"], key=lambda k: k.get("apply", 0))
        A(f"- 최고 효율 키워드: **{top['kw']}** (CTR {pct(top['ctr'])}, CPC {top['cpc']:,.0f}원).")
    A(f"- 노출점유율(IS) {pct(c['sis'])} · 예산손실 {pct(c['blost'])} · 순위손실 {pct(c['rlost'])}.\n")
    A("---\n")

    if p:
        A("## 2. 지난 기간 대비 (WoW)\n")
        A("| 지표 | 지난 | 이번 |")
        A("|---|---|---|")
        A(f"| CTR | {pct(p['ctr'])} | {pct(c['ctr'])} |")
        A(f"| 평균 CPC | {p['cpc']:,.0f}원 | {c['cpc']:,.0f}원 |")
        A(f"| 검색 노출점유율 | {pct(p['sis'])} | {pct(c['sis'])} |")
        A(f"| 예산손실 IS | {pct(p['blost'])} | {pct(c['blost'])} |")
        A(f"| 순위손실 IS | {pct(p['rlost'])} | {pct(c['rlost'])} |\n")
        A("![노출점유율 병목 변화](charts/4_is_wow.png)\n")
        A("---\n")

    A("## 3. 일별 추이\n")
    A("| 날짜 | 노출 | 클릭 | CTR | 비용 | CPC | 예산손실 | 순위손실 |")
    A("|---|---|---|---|---|---|---|---|")
    for d in data["daily"]:
        A(f"| {d['date']} | {d['imp']:,} | {d['clk']} | {pct(d['ctr'])} | {d['cost']:,.0f} | {d['cpc']:,.0f} | {pct(d['blost'])} | {pct(d['rlost'])} |")
    A("\n![일별 비용·클릭 추이](charts/1_daily.png)\n")
    A("---\n")

    A("## 4. 키워드별 성과 & 효율\n")
    A("> `신청클릭`=GA4 cta_apply_click(랜딩 신청버튼, 마이크로 전환). `신청클릭당 비용`=Ads 비용÷GA4 신청클릭.\n")
    A("| 키워드 | 매치 | 품질 | 노출 | 클릭 | CTR | 비용 | CPC | 신청클릭 | 신청단가 | 효율 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    for k in data["keywords"]:
        ap = int(k.get("apply", 0))
        cpa = f"{k['cpa']:,.0f}원" if k.get("cpa") else "-"
        gr = f"{GRADE_ICON[k['grade']]} {k['grade']}" if k.get("grade") else "-"
        A(f"| {k['kw']} | {k['match']} | {k['quality'] or '-'} | {k['imp']:,} | {k['clk']} | {pct(k['ctr'])} | {k['cost']:,.0f} | {k['cpc']:,.0f} | {ap} | {cpa} | {gr} |")
    A("\n![키워드별 비용 & CTR](charts/2_kw_cost_ctr.png)\n")
    A("![키워드별 신청클릭당 비용](charts/3_cost_per_apply.png)\n")
    A("> 효율 등급(S~C)은 신청단가·CTR 기준 휴리스틱. 최종 판단은 분석자가 조정.\n")
    A("---\n")

    A("## 5. 결론 & 액션 아이템\n")
    A("- (자동 생성 지표 기반. 분석자가 캠페인 맥락에 맞춰 액션을 확정하세요.)")
    worst = [k for k in data["keywords"] if k.get("grade") == "C"]
    if worst:
        A(f"- 개선 1순위: **{', '.join(k['kw'] for k in worst)}** (효율 C) — 정밀화·제외키워드·중지 검토.")
    if c["blost"] and c["blost"] > 0.15:
        A(f"- 예산손실 {pct(c['blost'])} — 예산 증액 여지.")
    if c["rlost"] and c["rlost"] > 0.3:
        A(f"- 순위손실 {pct(c['rlost'])} — 입찰·품질(랜딩·소재) 개선 필요(예산으로 해결 불가).")
    A("\n---\n")
    A(f"*Google Ads API + GA4 Data API 실데이터 기반 자동 생성 ({args.apply_event} 기준). 신청클릭은 마이크로 전환으로 최종 신청완료와 다를 수 있음.*")
    return "\n".join(lines)


# ---------- PDF (make-pdf, 차트 base64 임베드) ----------
def build_pdf(md_text, outdir, pdf_path, title, author):
    outdir = Path(outdir)

    def embed(m):
        rel = m.group(2)
        b = base64.b64encode((outdir / rel).read_bytes()).decode()
        return f"![{m.group(1)}](data:image/png;base64,{b})"
    md_b64 = re.sub(r"!\[([^\]]*)\]\((charts/[^)]+)\)", embed, md_text)
    tmp = outdir / ".report_b64.md"
    tmp.write_text(md_b64, encoding="utf-8")
    binp = os.environ.get("MAKE_PDF_BIN") or os.path.expanduser("~/.claude/skills/gstack/make-pdf/dist/pdf")
    if not os.path.exists(binp):
        print(f"[경고] make-pdf 바이너리 없음({binp}). MD만 생성됨.", file=sys.stderr)
        return False
    subprocess.run([binp, "generate", "--cover", "--toc", "--no-confidential",
                    "--title", title, "--author", author, "--date", datetime.date.today().isoformat(),
                    str(tmp), str(pdf_path)], check=True)
    tmp.unlink(missing_ok=True)
    return True


# ---------- 메인 ----------
def main():
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--cid", required=True)
    ap.add_argument("--ga4", required=True, help="GA4 property id (숫자만)")
    ap.add_argument("--yaml", required=True, help="google-ads.yaml 경로 (client_id/secret/refresh_token 포함)")
    ap.add_argument("--preset", default="this_week", choices=["this_week", "last_7_days", "last_14_days"])
    ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--title", default=None)
    ap.add_argument("--author", default="마케팅")
    ap.add_argument("--apply-event", default="cta_apply_click")
    ap.add_argument("--no-wow", action="store_true")
    args = ap.parse_args()

    s, e = resolve_period(args.preset, args.start, args.end)
    title = args.title or f"{args.campaign} — 키워드 광고 성과 리포트"
    Path(args.outdir).mkdir(parents=True, exist_ok=True)

    ga = ads_client(args.yaml).get_service("GoogleAdsService")
    cfg = yaml.safe_load(open(args.yaml))

    data = {"period": (s, e)}
    data["campaign"] = ads_campaign(ga, args.cid, args.campaign, s, e)
    if not data["campaign"]:
        sys.exit(f"[중단] 기간 {s}~{e} 캠페인 '{args.campaign}' 데이터 없음")
    data["daily"] = ads_daily(ga, args.cid, args.campaign, s, e)
    data["keywords"] = ads_keywords(ga, args.cid, args.campaign, s, e)
    if not args.no_wow:
        ps, pe = prev_period(s, e)
        data["campaign_prev"] = ads_campaign(ga, args.cid, args.campaign, ps, pe)

    # GA4 신청퍼널 병합
    tok = ga4_token(cfg)
    sess = ga4_keyword_metric(tok, args.ga4, s, e, "sessions")
    appl = ga4_keyword_metric(tok, args.ga4, s, e, "eventCount", event=args.apply_event)
    for k in data["keywords"]:
        key = k["kw"].lower()
        k["sessions"] = int(sess.get(key, 0))
        k["apply"] = int(appl.get(key, 0))
        k["cpa"] = (k["cost"] / k["apply"]) if k["apply"] else None
    # 효율 등급
    cpas = [k["cpa"] for k in data["keywords"] if k.get("cpa")]
    best = min(cpas) if cpas else None
    for k in data["keywords"]:
        k["grade"] = grade(k.get("cpa"), k["ctr"], best) if best else None

    make_charts(data, args.outdir)
    md = build_md(data, args)
    slug = re.sub(r"[^\w가-힣]+", "-", args.campaign).strip("-")
    md_path = Path(args.outdir) / f"{slug}-keyword-report-{e}.md"
    pdf_path = Path(args.outdir) / f"{slug}-keyword-report-{e}.pdf"
    md_path.write_text(md, encoding="utf-8")
    ok = build_pdf(md, args.outdir, pdf_path, title, args.author)
    print(f"[✓] MD: {md_path}")
    print(f"[✓] PDF: {pdf_path}" if ok else "[i] PDF 미생성(make-pdf 없음)")


if __name__ == "__main__":
    main()
