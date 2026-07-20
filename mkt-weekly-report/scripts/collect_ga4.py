# -*- coding: utf-8 -*-
"""주간 마케팅 리포트용 GA4 데이터 수집 → <workspace>/ga4_data.json

조코딩AX 사이트별 GA4 속성·CTA 이벤트를 실측 매핑으로 조회한다.
날짜창은 항상 실행일 기준 상대창(14daysAgo~yesterday). ga4_auth.py(마케팅 레포)를
재사용하므로 --ads-dir 로 그 위치를 지정한다(기본 ~/Desktop/dev/marketing/ads).
"""
import argparse
import json
import os
import sys
from pathlib import Path

DEF_ADS = os.path.expanduser("~/Desktop/dev/marketing/ads")

# 사이트 → GA4 속성 → CTA/전환 이벤트 (2026-07-13 실측 확정)
HOME = "538854394"    # jocodingax.ai            CTA = cta_click
HACK = "542898562"    # hackathon.jocodingax.ai  CTA = cta_apply_click → primer
PRIMER = "542884357"  # hack.primer.kr           신청 = form_submit (퍼널 종단)
BLOG = "529719326"    # blog.jocodingax.ai
D14 = ("14daysAgo", "yesterday")
D7 = ("7daysAgo", "yesterday")


def main() -> None:
    ap = argparse.ArgumentParser(description="주간 리포트용 GA4 수집")
    ap.add_argument("--ads-dir", default=DEF_ADS,
                    help="ga4_auth.py 가 있는 마케팅 ads 디렉터리 (기본 %(default)s)")
    ap.add_argument("--out", default=None,
                    help="출력 JSON 경로 (기본 <ads-dir>/../_workspace/ga4_data.json)")
    args = ap.parse_args()

    ads_dir = os.path.abspath(os.path.expanduser(args.ads_dir))
    if ads_dir not in sys.path:
        sys.path.insert(0, ads_dir)  # ga4_auth.ga4_client() 재사용 (토큰은 자기 위치 기준 해석)
    from ga4_auth import ga4_client  # noqa: E402
    from google.analytics.data_v1beta.types import (  # noqa: E402
        DateRange, Dimension, Filter, FilterExpression, FilterExpressionList,
        Metric, OrderBy, RunReportRequest)

    out = args.out or os.path.join(ads_dir, "..", "_workspace", "ga4_data.json")
    out = os.path.abspath(out)
    c = ga4_client()

    def eq(f, v):
        return FilterExpression(filter=Filter(field_name=f, string_filter=Filter.StringFilter(value=v)))

    def AND(*e):
        return FilterExpression(and_group=FilterExpressionList(expressions=list(e)))

    def rep(pid, dims, mets, dr, filt=None, order=None, limit=200):
        req = RunReportRequest(
            property=f"properties/{pid}",
            date_ranges=[DateRange(start_date=dr[0], end_date=dr[1])],
            dimensions=[Dimension(name=d) for d in dims],
            metrics=[Metric(name=m) for m in mets],
            dimension_filter=filt,
            order_bys=[order] if order else None,
            limit=limit)
        r = c.run_report(req)
        return [{"d": [v.value for v in row.dimension_values],
                 "m": [v.value for v in row.metric_values]} for row in r.rows]

    def by_metric(m, desc=True):
        return OrderBy(metric=OrderBy.MetricOrderBy(metric_name=m), desc=desc)

    def by_dim(d):
        return OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name=d))

    data = {}

    # 1. jocodingax.ai 일별 세션 + cta_click
    sess = rep(HOME, ["date"], ["sessions", "totalUsers"], D14, order=by_dim("date"))
    cta = rep(HOME, ["date"], ["eventCount"], D14, filt=eq("eventName", "cta_click"), order=by_dim("date"))
    ctam = {r["d"][0]: int(r["m"][0]) for r in cta}
    data["home_daily"] = [{"date": r["d"][0], "sessions": int(r["m"][0]), "users": int(r["m"][1]),
                           "cta": ctam.get(r["d"][0], 0)} for r in sess]

    # 2. 해커톤 일별 세션 + cta_apply_click(프라이머 이동)
    sess = rep(HACK, ["date"], ["sessions", "totalUsers"], D14, order=by_dim("date"))
    cta = rep(HACK, ["date"], ["eventCount"], D14, filt=eq("eventName", "cta_apply_click"), order=by_dim("date"))
    ctam = {r["d"][0]: int(r["m"][0]) for r in cta}
    data["hack_daily"] = [{"date": r["d"][0], "sessions": int(r["m"][0]), "users": int(r["m"][1]),
                           "cta": ctam.get(r["d"][0], 0)} for r in sess]

    # 3. jocodingax.ai 소스별(source+medium) 세션·이탈률·cta_click
    sess = rep(HOME, ["sessionSource", "sessionMedium"], ["sessions", "bounceRate", "totalUsers"], D14, order=by_metric("sessions"), limit=200)
    cta = rep(HOME, ["sessionSource", "sessionMedium"], ["eventCount"], D14, filt=eq("eventName", "cta_click"), limit=300)
    ctam = {(r["d"][0], r["d"][1]): int(r["m"][0]) for r in cta}
    data["home_source"] = [{"source": r["d"][0], "medium": r["d"][1], "sessions": int(r["m"][0]),
                            "bounce": round(float(r["m"][1]) * 100, 1), "users": int(r["m"][2]),
                            "cta": ctam.get((r["d"][0], r["d"][1]), 0)} for r in sess]

    # 3b. jocodingax.ai 유입경로(채널그룹)별 세션·이탈률·cta_click
    ch = rep(HOME, ["sessionDefaultChannelGroup"], ["sessions", "bounceRate", "totalUsers"], D14, order=by_metric("sessions"), limit=30)
    chcta = rep(HOME, ["sessionDefaultChannelGroup"], ["eventCount"], D14, filt=eq("eventName", "cta_click"), limit=30)
    chctam = {r["d"][0]: int(r["m"][0]) for r in chcta}
    data["home_channel"] = [{"channel": r["d"][0], "sessions": int(r["m"][0]),
                             "bounce": round(float(r["m"][1]) * 100, 1), "users": int(r["m"][2]),
                             "cta": chctam.get(r["d"][0], 0)} for r in ch]

    # 4. 해커톤 전체 UTM 분해(source/medium/campaign/content) 세션·이탈률 + cta_apply_click
    sess = rep(HACK, ["sessionSource", "sessionMedium", "sessionCampaignName", "sessionManualAdContent"],
               ["sessions", "totalUsers", "bounceRate"], D14, order=by_metric("sessions"), limit=200)
    cta = rep(HACK, ["sessionSource", "sessionMedium", "sessionCampaignName", "sessionManualAdContent"],
              ["eventCount"], D14, filt=eq("eventName", "cta_apply_click"), limit=300)
    ctam = {tuple(r["d"]): int(r["m"][0]) for r in cta}
    data["hack_utm"] = [{"source": r["d"][0], "medium": r["d"][1], "campaign": r["d"][2], "content": r["d"][3],
                         "sessions": int(r["m"][0]), "users": int(r["m"][1]),
                         "bounce": round(float(r["m"][2]) * 100, 1),
                         "cta": ctam.get(tuple(r["d"]), 0)} for r in sess]

    # 5. 해커톤 소스(플랫폼)별 세션·이탈률·cta
    sess = rep(HACK, ["sessionSource", "sessionMedium"], ["sessions", "bounceRate", "totalUsers"], D14, order=by_metric("sessions"), limit=200)
    cta = rep(HACK, ["sessionSource", "sessionMedium"], ["eventCount"], D14, filt=eq("eventName", "cta_apply_click"), limit=300)
    ctam = {(r["d"][0], r["d"][1]): int(r["m"][0]) for r in cta}
    data["hack_source"] = [{"source": r["d"][0], "medium": r["d"][1], "sessions": int(r["m"][0]),
                            "bounce": round(float(r["m"][1]) * 100, 1), "users": int(r["m"][2]),
                            "cta": ctam.get((r["d"][0], r["d"][1]), 0)} for r in sess]

    # 6. 프라이머 퍼널 종단: hack.primer.kr form_submit
    fs = rep(PRIMER, ["date"], ["eventCount"], D14, filt=eq("eventName", "form_submit"), order=by_dim("date"))
    data["primer_form_submit_14d"] = sum(int(r["m"][0]) for r in fs)
    tot = rep(PRIMER, [], ["sessions"], D14)
    data["primer_sessions_14d"] = int(tot[0]["m"][0]) if tot else 0

    # 7. google/cpc → jocodingax.ai 랜딩 페이지별 이탈률
    lp = rep(HOME, ["landingPagePlusQueryString"], ["sessions", "bounceRate", "totalUsers"], D14,
             filt=AND(eq("sessionSource", "google"), eq("sessionMedium", "cpc")),
             order=by_metric("sessions"), limit=40)
    data["home_cpc_landing"] = [{"page": r["d"][0], "sessions": int(r["m"][0]),
                                 "bounce": round(float(r["m"][1]) * 100, 1), "users": int(r["m"][2])} for r in lp]
    g = rep(HOME, ["sessionMedium"], ["sessions", "bounceRate"], D14, filt=eq("sessionSource", "google"), limit=20)
    data["home_google"] = [{"medium": r["d"][0], "sessions": int(r["m"][0]), "bounce": round(float(r["m"][1]) * 100, 1)} for r in g]

    # 8. blog.jocodingax.ai 자체 성과
    b = rep(BLOG, ["date"], ["sessions", "totalUsers"], D14, order=by_dim("date"))
    data["blog_daily"] = [{"date": r["d"][0], "sessions": int(r["m"][0]), "users": int(r["m"][1])} for r in b]
    bp = rep(BLOG, ["pagePath"], ["screenPageViews", "sessions", "bounceRate"], D14, order=by_metric("screenPageViews"), limit=15)
    data["blog_top_pages"] = [{"path": r["d"][0], "views": int(r["m"][0]), "sessions": int(r["m"][1]),
                               "bounce": round(float(r["m"][2]) * 100, 1)} for r in bp]
    bc = rep(BLOG, ["sessionDefaultChannelGroup"], ["sessions", "bounceRate"], D14, order=by_metric("sessions"), limit=15)
    data["blog_channels"] = [{"channel": r["d"][0], "sessions": int(r["m"][0]), "bounce": round(float(r["m"][1]) * 100, 1)} for r in bc]

    # 9. 블로그 → 본사이트(jocodingax.ai) 리퍼럴
    br = rep(HOME, ["sessionSource", "sessionMedium"], ["sessions", "bounceRate"], D14, limit=200)
    data["home_blog_referral"] = [{"source": r["d"][0], "medium": r["d"][1], "sessions": int(r["m"][0]),
                                   "bounce": round(float(r["m"][1]) * 100, 1)} for r in br
                                  if "blog" in r["d"][0].lower() or "inblog" in r["d"][0].lower() or r["d"][1] == "blog"]

    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"saved {out}")
    h = data["home_daily"]; k = data["hack_daily"]
    print(f"HOME 14d: sessions={sum(x['sessions'] for x in h)} cta_click={sum(x['cta'] for x in h)}")
    print(f"HACK 14d: sessions={sum(x['sessions'] for x in k)} cta_apply_click={sum(x['cta'] for x in k)}")
    print(f"PRIMER 14d: sessions={data['primer_sessions_14d']} form_submit={data['primer_form_submit_14d']}")
    print(f"BLOG 14d: sessions={sum(x['sessions'] for x in data['blog_daily'])}")


if __name__ == "__main__":
    main()
