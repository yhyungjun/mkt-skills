# email-sms — Resend transactional email / Octomo reverse-SMS OTP

> Brand-neutral templates extracted from `granter-landing` (apps/web).
> Snapshot: 2026-06-11. Source repo: a Next.js (App Router) Korean landing page.
> Replace every `__PLACEHOLDER__` token. Keys come from env, never hardcode secrets.
>
> Files in this doc:
> - `lib/email.ts` — Resend `sendPaymentConfirmEmail` + HTML builder (null-stub)
> - `lib/octomo.ts` — Octomo **reverse-SMS** verify (`checkOctomoMessage`)
> - `app/api/otp/send/route.ts` — issue 4-digit code (cooldown 30s / TTL 5min)
> - `app/api/otp/verify/route.ts` — confirm via Octomo, mark user verified

The OTP flow here is **reverse SMS**: the server issues a code, the *user* texts
that code to a published number, and the server polls Octomo to confirm the
inbound message exists. No outbound SMS gateway is needed.

---

## `lib/email.ts`

Source: `apps/web/lib/email.ts`.
Replacement points: `__SITE_URL__` fallback, `__DOWNLOAD_URL__` path,
`__FREE_LECTURE_URL__`, `from`/`subject` strings, and all body copy.
Env: `RESEND_API_KEY`, `NEXT_PUBLIC_SITE_URL`.

PRESERVE: `getResend()` returns `null` when the key is missing and the sender
skips (returns `{ success:false }`) instead of throwing — same stub philosophy as
the Supabase admin. The function returns a `{ success, error? }` result envelope.

```ts
import { Resend } from "resend";

function getResend(): Resend | null {
  const key = process.env.RESEND_API_KEY;
  if (!key) return null;
  return new Resend(key);
}

const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? "__SITE_URL__"; // e.g. https://example.com

const DOWNLOAD_URL = `${SITE_URL}/downloads/__ASSET__.zip`;

const FREE_LECTURE_URL = "__FREE_LECTURE_URL__"; // TODO: 실제 무료 강의 URL로 교체

function buildPaymentConfirmHtml(name: string): string {
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.7;color:#222;max-width:600px;margin:0 auto;padding:20px;">

<p>${name}님, 안녕하세요.</p>
<p><strong>__PRODUCT_NAME__</strong> 결제가 완료되었습니다. 감사합니다!</p>

<h3 style="color:#333;margin-top:24px;">무료 선물: __GIFT_NAME__</h3>
<p>결제 감사 선물로 <strong>__GIFT_DESC__</strong>을 드립니다. 아래 버튼을 눌러 다운로드하세요.</p>

<p style="margin:24px 0;">
  <a href="${DOWNLOAD_URL}" style="display:inline-block;padding:14px 28px;background:#222;color:#fff;text-decoration:none;font-weight:600;font-size:15px;">
    __DOWNLOAD_LABEL__ (ZIP)
  </a>
</p>

<h3 style="color:#333;margin-top:24px;">시작은 3단계</h3>
<p style="margin-bottom:4px;">(자세한 건 zip 안 사용법 PDF에 그림으로 담았어요)</p>
<ol style="padding-left:20px;">
  <li>__STEP_1__ — 처음이시면 <a href="${FREE_LECTURE_URL}" style="color:#2563eb;">무료 강의</a>부터</li>
  <li>__STEP_2__</li>
  <li>__STEP_3__</li>
</ol>

<hr style="border:none;border-top:1px solid #eee;margin:28px 0;">

<h3 style="color:#333;">강의 안내</h3>
<p>강의 시작 전 일정·장소 안내를 별도로 보내드립니다.<br>
궁금한 점은 이 메일에 회신해 주세요.</p>

<p>감사합니다.<br><strong>__TEAM_SIGNATURE__</strong></p>

</body></html>`;
}

export async function sendPaymentConfirmEmail(
  email: string,
  name: string,
): Promise<{ success: boolean; error?: string }> {
  const resend = getResend();
  if (!resend) {
    console.warn("[email] RESEND_API_KEY not configured, skipping email");
    return { success: false, error: "RESEND_API_KEY not configured" };
  }

  try {
    const { error } = await resend.emails.send({
      from: "__FROM_NAME__ <noreply@__DOMAIN__>",
      to: email,
      subject: "__SUBJECT__",
      html: buildPaymentConfirmHtml(name),
    });

    if (error) {
      console.error("[email] Resend error:", error);
      return { success: false, error: error.message };
    }

    return { success: true };
  } catch (e) {
    const msg = e instanceof Error ? e.message : "Unknown email error";
    console.error("[email] Send failed:", msg);
    return { success: false, error: msg };
  }
}
```

---

## `lib/octomo.ts`

Source: `apps/web/lib/octomo.ts`.
Replacement points: `__OCTOMO_PHONE__` (the published inbound number),
`__USER_AGENT__`. Env: `OCTOMO_API_KEY`.

PRESERVE: digit-only normalization (`replace(/[^0-9]/g, "")`), the
`Authorization: Octomo ${apiKey}` header scheme, and the `data.exists === true`
check. Returns `false` (not throw) on missing key or non-OK response.

```ts
import "server-only";

const OCTOMO_URL = "https://api.octoverse.kr/octomo/v1/public/message/exists";

/** OCTOMO 대표번호 — 사용자가 문자를 보낼 번호 */
export const OCTOMO_PHONE = "__OCTOMO_PHONE__"; // e.g. "1666-3538"

/**
 * OCTOMO API로 문자 수신 여부 확인.
 * 사용자가 OCTOMO_PHONE으로 text를 보냈는지 검증.
 */
export async function checkOctomoMessage(
  mobileNum: string,
  text: string,
): Promise<boolean> {
  const apiKey = process.env.OCTOMO_API_KEY ?? "";
  if (!apiKey) {
    console.error("[octomo] Missing OCTOMO_API_KEY env var");
    return false;
  }

  const phone = mobileNum.replace(/[^0-9]/g, "");

  const res = await fetch(OCTOMO_URL, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "User-Agent": "__USER_AGENT__", // e.g. "my-landing/1.0"
      Authorization: `Octomo ${apiKey}`,
    },
    body: JSON.stringify({ mobileNum: phone, text }),
  });

  if (!res.ok) {
    const body = await res.text();
    console.error("[octomo] API failed:", res.status, body);
    return false;
  }

  const data = await res.json();
  return data.exists === true;
}
```

---

## `app/api/otp/send/route.ts`

Source: `apps/web/app/api/otp/send/route.ts`.
Depends on `@/lib/auth` (session), `requireSupabaseAdmin`, `OCTOMO_PHONE`.

PRESERVE EXACTLY: `OTP_EXPIRE_MINUTES = 5`, `OTP_COOLDOWN_SECONDS = 30`, the
phone regex `/^010\d{8}$/`, crypto-random 4-digit code zero-padded, the cooldown
query against `otp_codes.created_at`, and the 429 on cooldown hit. Requires an
authenticated session (401 otherwise).

NOTE: the response returns `code` to the client — this is intentional for the
reverse-SMS flow (the UI shows the code for the user to text out). Keep that in
mind for any privacy review; do not "fix" it without understanding the flow.

```ts
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { requireSupabaseAdmin } from "@/lib/supabase/server";
import { OCTOMO_PHONE } from "@/lib/octomo";

const OTP_EXPIRE_MINUTES = 5;
const OTP_COOLDOWN_SECONDS = 30;

function generateCode(): string {
  const array = new Uint32Array(1);
  crypto.getRandomValues(array);
  return String(array[0] % 10000).padStart(4, "0");
}

export async function POST(req: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();
  const phone = String(body.phone ?? "").replace(/[^0-9]/g, "");

  if (!/^010\d{8}$/.test(phone)) {
    return NextResponse.json({ error: "올바른 휴대폰 번호를 입력해주세요." }, { status: 400 });
  }

  const supabase = requireSupabaseAdmin();

  // 쿨다운 체크
  const cooldownCutoff = new Date(Date.now() - OTP_COOLDOWN_SECONDS * 1000).toISOString();
  const { data: recent } = await supabase
    .from("otp_codes")
    .select("id")
    .eq("phone", phone)
    .gte("created_at", cooldownCutoff)
    .limit(1);

  if (recent && recent.length > 0) {
    return NextResponse.json({ error: "잠시 후 다시 시도해주세요." }, { status: 429 });
  }

  const code = generateCode();
  const expiresAt = new Date(Date.now() + OTP_EXPIRE_MINUTES * 60 * 1000).toISOString();

  await supabase.from("otp_codes").insert({
    phone,
    code,
    expires_at: expiresAt,
  });

  return NextResponse.json({
    ok: true,
    code,
    octomoPhone: OCTOMO_PHONE,
    expiresIn: OTP_EXPIRE_MINUTES * 60,
  });
}
```

---

## `app/api/otp/verify/route.ts`

Source: `apps/web/app/api/otp/verify/route.ts`.

PRESERVE: verification is delegated to `checkOctomoMessage(phone, code)` (did the
user text the code in?), phone is re-formatted to `010-XXXX-XXXX` for storage,
`onboarded_at` is set on first verify only, and matching `otp_codes` rows are
marked `used: true`. Requires an authenticated session (401 otherwise).

```ts
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { requireSupabaseAdmin } from "@/lib/supabase/server";
import { checkOctomoMessage } from "@/lib/octomo";

export async function POST(req: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();
  const phone = String(body.phone ?? "").replace(/[^0-9]/g, "");
  const code = String(body.code ?? "").trim();

  if (!phone || !code) {
    return NextResponse.json({ error: "인증 정보가 부족합니다." }, { status: 400 });
  }

  // OCTOMO API로 문자 수신 확인
  const verified = await checkOctomoMessage(phone, code);

  if (!verified) {
    return NextResponse.json({ error: "인증에 실패했습니다. 문자를 보낸 후 다시 시도해주세요." }, { status: 400 });
  }

  const supabase = requireSupabaseAdmin();

  // users 테이블에 인증 완료 반영 + 첫 방문이면 onboarded_at도 설정
  const formattedPhone = `${phone.slice(0, 3)}-${phone.slice(3, 7)}-${phone.slice(7)}`;
  const { data: current } = await supabase
    .from("users")
    .select("onboarded_at")
    .eq("id", session.user.id)
    .maybeSingle();

  const patch: Record<string, unknown> = { phone: formattedPhone, phone_verified: true };
  if (!current?.onboarded_at) {
    patch.onboarded_at = new Date().toISOString();
  }
  await supabase.from("users").update(patch).eq("id", session.user.id);

  // otp_codes 사용 처리
  await supabase
    .from("otp_codes")
    .update({ used: true })
    .eq("phone", phone)
    .eq("code", code)
    .eq("used", false);

  return NextResponse.json({ ok: true });
}
```
