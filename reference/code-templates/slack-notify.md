# 운영자용 Slack 신청 알림 (Incoming Webhook · Block Kit)

> **출처**: 강의 랜딩 사례 (`lib/notify.ts`). 신규 신청이 들어오면 운영 Slack 채널로 즉시 알림.
> **왜**: 어드민을 안 봐도 신청을 실시간 인지 → 빠른 입금 확인·응대. 이메일 자동발송(고객용)과 별개의 **운영자용** 채널.
> **핵심**: ① Webhook URL은 **시크릿으로만** 주입(코드/리포 금지). ② 미설정 시 **스텁**(스킵)으로 빌드·로컬 무해.
> ③ **Incoming Webhook은 `actions`(대화형 버튼) 사용 시 경고** → 링크는 `actions` 대신 **mrkdwn 링크**로(기능 동일).

---

## lib/notify.ts (paste-ready)

```ts
import "server-only";
import { EVENT, SITE } from "./config";

export interface ApplicationAlert {
  name: string; phone: string; email: string;
  job_title: string | null; business_name: string | null; business_number: string | null;
  needs_tax_invoice: boolean; tax_invoice_email: string | null;
  region: string | null; channel: string | null;
  expectations: string | null; message: string | null;
}

// Slack mrkdwn 이스케이프 (& < > 만 처리하면 충분)
const esc = (v: string | null | undefined): string =>
  String(v ?? "-").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const field = (label: string, value: string) => ({
  type: "mrkdwn" as const, text: `*${label}*\n${value}`,
});

function nowKST(): string {
  try {
    return new Intl.DateTimeFormat("ko-KR", {
      timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short",
    }).format(new Date());
  } catch { return new Date().toISOString(); }
}

export async function sendSlackApplicationAlert(a: ApplicationAlert): Promise<void> {
  const url = process.env.SLACK_APPLICATIONS_WEBHOOK_URL;
  if (!url) {
    console.log("[slack stub] SLACK_APPLICATIONS_WEBHOOK_URL 미설정 — 알림 스킵");
    return; // 스텁 — 시크릿 없을 때 무해
  }

  const business = a.business_number
    ? `${esc(a.business_name)} · ${esc(a.business_number)}`
    : esc(a.business_name);

  const fields = [
    field("이름", esc(a.name)), field("연락처", esc(a.phone)), field("이메일", esc(a.email)),
    field("사업자", business), field("직무·직책", esc(a.job_title)),
    field("세금계산서", a.needs_tax_invoice ? "필요" : "불필요"),
    field("지역", esc(a.region)), field("유입", esc(a.channel)),
  ];
  if (a.needs_tax_invoice && a.tax_invoice_email)
    fields.push(field("세금계산서 이메일", esc(a.tax_invoice_email)));

  type Block = Record<string, unknown>;
  const blocks: Block[] = [
    { type: "header", text: { type: "plain_text", text: `🎉 새 신청 접수 · ${EVENT.title}`, emoji: true } },
    { type: "section", fields },
  ];
  if (a.expectations)
    blocks.push({ type: "section", text: { type: "mrkdwn", text: `*기대하는 점*\n${esc(a.expectations)}` } });
  if (a.message)
    blocks.push({ type: "section", text: { type: "mrkdwn", text: `*자유 의견*\n${esc(a.message)}` } });

  // 링크는 actions 버튼 대신 mrkdwn 링크로 — Incoming Webhook 대화형 경고 회피(기능 동일).
  blocks.push({
    type: "context",
    elements: [{ type: "mrkdwn", text: `🕒 ${nowKST()} (KST)  ·  <${SITE.url}/admin/applications|🔗 어드민에서 보기>` }],
  });

  const payload = {
    text: `새 신청 접수: ${a.name} (${a.business_name ?? "-"})`, // 알림 미리보기/폴백
    blocks,
  };

  try {
    const res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    });
    if (!res.ok) console.error("[slack]", res.status, await res.text());
  } catch (e) {
    console.error("[slack] send failed", e);
  }
}
```

## 배선 — `/api/applications` POST에서 INSERT 성공 직후 호출

```ts
import { sendSlackApplicationAlert } from "@/lib/notify";
// …insert 성공 후…
await sendApplicationEmail(email, name, variant); // 고객용 메일
await sendSlackApplicationAlert(row);             // 운영자용 Slack
```

## 외부 설정 (Slack 콘솔)
1. Slack App → **Incoming Webhooks** 활성화 → 대상 채널 선택 → Webhook URL 발급.
2. 배포 시크릿에 `SLACK_APPLICATIONS_WEBHOOK_URL` 등록(Cloudflare `wrangler secret put` / Vercel env). **vars(public) 아님.**
3. E2E: 테스트 신청 1건 → 채널 수신 확인 → 테스트 데이터 정리.

## 함정
- **`actions` 블록(버튼)**을 Incoming Webhook에 쓰면 Slack이 "대화형은 앱 필요" 경고를 띄움 → 링크는 mrkdwn으로.
- Webhook URL이 곧 발행 권한 → **노출 금지·유출 시 즉시 재발급**. 알림 실패는 신청 저장을 막지 않도록 try/catch로 격리(위 코드).
- 채널 변경/웹훅 갱신 시 시크릿만 교체하면 됨(코드 무변경).
