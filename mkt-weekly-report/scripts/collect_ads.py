# -*- coding: utf-8 -*-
"""주간 마케팅 리포트용 구글애즈 데이터 수집 → <workspace>/ads_data.json

조코딩AX 계정(CID 8834896313) 기본값. 인증은 google-ads.yaml(ADC/refresh token).
날짜창은 LAST_7_DAYS / LAST_14_DAYS 상대창.
"""
import argparse
import json
import os
from pathlib import Path

from google.ads.googleads.client import GoogleAdsClient

DEF_ADS = os.path.expanduser("~/Desktop/dev/marketing/ads")
DEF_CID = "8834896313"


def won(x: int) -> int:
    return round(x / 1_000_000)


def main() -> None:
    ap = argparse.ArgumentParser(description="주간 리포트용 구글애즈 수집")
    ap.add_argument("--ads-dir", default=DEF_ADS, help="google-ads.yaml 이 있는 디렉터리 (기본 %(default)s)")
    ap.add_argument("--yaml", default=None, help="google-ads.yaml 경로 (기본 <ads-dir>/google-ads.yaml)")
    ap.add_argument("--cid", default=DEF_CID, help="구글애즈 고객 ID (기본 조코딩AX %(default)s)")
    ap.add_argument("--out", default=None, help="출력 JSON (기본 <ads-dir>/../_workspace/ads_data.json)")
    args = ap.parse_args()

    ads_dir = os.path.abspath(os.path.expanduser(args.ads_dir))
    yaml_path = os.path.abspath(os.path.expanduser(args.yaml or os.path.join(ads_dir, "google-ads.yaml")))
    out = os.path.abspath(args.out or os.path.join(ads_dir, "..", "_workspace", "ads_data.json"))
    cid = args.cid

    client = GoogleAdsClient.load_from_storage(yaml_path)
    ga = client.get_service("GoogleAdsService")
    data = {}

    def daily(rng):
        d = {}
        for r in ga.search(customer_id=cid, query=f"""
            SELECT segments.date, metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.conversions
            FROM campaign WHERE segments.date DURING {rng}"""):
            s = r.segments.date
            a = d.setdefault(s, {"cost": 0, "clicks": 0, "impr": 0, "conv": 0.0})
            a["cost"] += r.metrics.cost_micros; a["clicks"] += r.metrics.clicks
            a["impr"] += r.metrics.impressions; a["conv"] += r.metrics.conversions
        return [{"date": k, "cost": won(v["cost"]), "clicks": v["clicks"], "impr": v["impr"],
                 "conv": round(v["conv"], 1)} for k, v in sorted(d.items())]

    data["daily_7d"] = daily("LAST_7_DAYS")
    data["daily_14d"] = daily("LAST_14_DAYS")

    camps = []
    for r in ga.search(customer_id=cid, query="""
        SELECT campaign.name, campaign.status, metrics.impressions, metrics.clicks,
               metrics.cost_micros, metrics.ctr, metrics.average_cpc, metrics.conversions,
               metrics.search_impression_share
        FROM campaign WHERE segments.date DURING LAST_14_DAYS AND metrics.impressions>0
        ORDER BY metrics.cost_micros DESC"""):
        c, m = r.campaign, r.metrics
        camps.append({"name": c.name, "status": c.status.name, "impr": m.impressions, "clicks": m.clicks,
                      "cost": won(m.cost_micros), "ctr": round(m.ctr * 100, 1), "cpc": won(m.average_cpc),
                      "conv": round(m.conversions, 1),
                      "is": round(m.search_impression_share * 100, 1) if m.search_impression_share else None})
    data["campaigns_14d"] = camps

    kws = []
    for r in ga.search(customer_id=cid, query="""
        SELECT campaign.name, ad_group_criterion.keyword.text, metrics.impressions, metrics.clicks,
               metrics.cost_micros, metrics.ctr, metrics.average_cpc, metrics.conversions,
               ad_group_criterion.quality_info.quality_score
        FROM keyword_view WHERE segments.date DURING LAST_14_DAYS AND metrics.impressions>0
        ORDER BY metrics.cost_micros DESC LIMIT 25"""):
        m = r.metrics
        kws.append({"campaign": r.campaign.name, "kw": r.ad_group_criterion.keyword.text,
                    "impr": m.impressions, "clicks": m.clicks, "cost": won(m.cost_micros),
                    "ctr": round(m.ctr * 100, 1), "cpc": won(m.average_cpc), "conv": round(m.conversions, 1),
                    "qs": r.ad_group_criterion.quality_info.quality_score or None})
    data["keywords_14d"] = kws

    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"saved {out}")
    t7 = data["daily_7d"]
    print(f"7d: cost={sum(x['cost'] for x in t7):,} clicks={sum(x['clicks'] for x in t7)} conv={sum(x['conv'] for x in t7):.1f}")
    print("campaigns:", [(c['name'], c['cost'], c['clicks']) for c in camps])


if __name__ == "__main__":
    main()
