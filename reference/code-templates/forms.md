# forms — applications API route / preorder Server Action

> Brand-neutral templates extracted from `granter-landing` (apps/web).
> Snapshot: 2026-06-11. Source repo: a Next.js (App Router) Korean landing page.
> Replace every `__PLACEHOLDER__` token. Keys come from env, never hardcode secrets.
>
> Files in this doc:
> - `app/api/applications/route.ts` — public application POST (validate + stub)
> - `app/preorder/page.tsx` — `submitPreorder` Server Action (+ supporting actions)

Both write to the same `applications` table. The API route is for an
unauthenticated landing form; the Server Action is for the logged-in pre-order
flow with survey fields and duplicate-prevention.

---

## `app/api/applications/route.ts`

Source: `apps/web/app/api/applications/route.ts`.
Replacement points: `__COHORT__` (cohort tag, e.g. `"beta-2026"`).
Env: `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

PRESERVE: input validation order (parse JSON → trim strings → required check →
email regex), the email regex `/^[^@\s]+@[^@\s]+\.[^@\s]+$/`, marketing-consent
coercion (`=== true || === "on"`), the **stub branch** (no Supabase env →
`console.warn` + `{ ok:true, stub:true }`), and the direct PostgREST `fetch`
insert with `Prefer: return=representation`. `getErrorMessage` narrows `unknown`.

```ts
import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { getSupabaseAdmin } from "@/lib/supabase/server";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

type ApplicationInput = {
  name?: unknown;
  email?: unknown;
  phone?: unknown;
  marketing_consent?: unknown;
};

function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return "알 수 없는 오류";
}

export async function POST(request: Request) {
  let body: ApplicationInput;
  try {
    body = (await request.json()) as ApplicationInput;
  } catch {
    return NextResponse.json({ error: "잘못된 요청 본문" }, { status: 400 });
  }

  const name = typeof body.name === "string" ? body.name.trim() : "";
  const email = typeof body.email === "string" ? body.email.trim() : "";
  const phone = typeof body.phone === "string" ? body.phone.trim() : "";
  const consent = body.marketing_consent === true || body.marketing_consent === "on";

  if (!name || !email || !phone) {
    return NextResponse.json({ error: "모든 항목을 입력해 주세요." }, { status: 400 });
  }
  if (!EMAIL_RE.test(email)) {
    return NextResponse.json({ error: "이메일 형식을 확인해 주세요." }, { status: 400 });
  }

  const session = await auth();
  const userId =
    session?.user?.role === "user" && session.user.id ? session.user.id : null;

  const supabase = getSupabaseAdmin();
  if (!supabase) {
    console.warn("[applications] Supabase env not configured. Logging only:", {
      userId,
      name,
      email,
      phone,
      consent,
    });
    return NextResponse.json({ ok: true, stub: true });
  }

  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL}/rest/v1/applications`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: process.env.SUPABASE_SERVICE_ROLE_KEY ?? "",
        Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY ?? ""}`,
        Prefer: "return=representation",
      },
      body: JSON.stringify({
        user_id: userId,
        name,
        email,
        phone,
        marketing_consent: consent,
        status: "pending",
        cohort: "__COHORT__", // e.g. "beta-2026"
      }),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Supabase ${res.status}: ${text}`);
    }
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[applications] insert failed:", err);
    return NextResponse.json(
      { error: `신청 저장 중 오류: ${getErrorMessage(err)}` },
      { status: 500 }
    );
  }
}
```

---

## `app/preorder/page.tsx` — Server Actions

Source: `apps/web/app/preorder/page.tsx`.
Replacement points: `__BRAND__` (metadata), `__COHORT__`, and the survey field
names / "기타" (other) sentinel if your survey differs. Depends on `@/lib/auth`,
`getSupabaseAdmin`, `PAYMENT_ENABLED`, and a `SurveyForm` client component that
calls the action.

PRESERVE: the gating chain — `PAYMENT_ENABLED` redirects `/preorder` → `/pay`;
unauthenticated → `/signin?from=/preorder`; missing `onboarded_at` →
`/onboarding`; duplicate pre-order (same `user_id` + cohort + `is_preorder`) →
`/preorder/done` without re-inserting. Supabase-null branches degrade gracefully
(stub mode). The "기타" handling for region/status/channels and the
`getAll()`-into-array survey mapping are load-bearing for the survey schema.

Only the two Server Actions and the page guard are shown (the JSX layout is
brand-specific copy — rebuild per design).

```tsx
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import { PAYMENT_ENABLED } from "@/lib/config";
import { SurveyForm } from "./SurveyForm";

export const metadata = {
  title: "사전예약 | __BRAND__",
  description: "정식 오픈 전 사전예약. 우선 결제 안내 + 사전예약 한정 무료 자료.",
};

async function enableMarketingConsent() {
  "use server";
  const session = await auth();
  if (!session?.user?.id) redirect("/signin?from=/preorder");

  const supabase = getSupabaseAdmin();
  if (!supabase) redirect("/preorder");

  await supabase
    .from("users")
    .update({ marketing_consent: true })
    .eq("id", session.user.id);

  redirect("/preorder");
}

async function submitPreorder(formData: FormData) {
  "use server";
  const session = await auth();
  if (!session?.user?.id) redirect("/signin?from=/preorder");

  const supabase = getSupabaseAdmin();
  if (!supabase) {
    console.warn("[preorder] Supabase not configured.");
    redirect("/preorder/done");
  }

  const { data: user } = await supabase
    .from("users")
    .select("id, name, email, phone, marketing_consent, onboarded_at")
    .eq("id", session.user.id)
    .maybeSingle();

  if (!user) redirect("/signin?from=/preorder");
  if (!user.onboarded_at) redirect("/onboarding");

  // 이미 사전예약했으면 중복 INSERT 방지
  const { data: existing } = await supabase
    .from("applications")
    .select("id")
    .eq("user_id", user.id)
    .eq("cohort", "__COHORT__") // e.g. "beta-2026"
    .eq("is_preorder", true)
    .maybeSingle();

  if (!existing) {
    await supabase.from("applications").insert({
      user_id: user.id,
      name: user.name ?? "",
      email: user.email,
      phone: user.phone ?? "",
      marketing_consent: user.marketing_consent ?? false,
      cohort: "__COHORT__",
      status: "pending",
      is_preorder: true,
      survey_format: formData.get("survey_format") as string | null,
      survey_days: formData.getAll("survey_days") as string[],
      survey_times: formData.getAll("survey_times") as string[],
      survey_region: formData.get("survey_region") === "기타"
        ? (formData.get("survey_region_other") as string) ?? "기타"
        : (formData.get("survey_region") as string | null),
      survey_status: formData.get("survey_status") === "기타"
        ? (formData.get("survey_status_other") as string) ?? "기타"
        : (formData.get("survey_status") as string | null),
      survey_channels: [
        ...(formData.getAll("survey_channels") as string[]).filter(
          (v) => v !== "기타"
        ),
        ...(formData.get("survey_channels_other")
          ? [(formData.get("survey_channels_other") as string)]
          : formData.getAll("survey_channels").includes("기타")
            ? ["기타"]
            : []),
      ],
      survey_revenue: formData.get("survey_revenue") as string | null,
      survey_granter: formData.get("survey_granter") as string | null,
      survey_interests: formData.getAll("survey_interests") as string[],
      survey_comment: formData.get("survey_comment") as string | null,
    });
  }

  redirect("/preorder/done");
}

export default async function PreorderPage() {
  // 정식 오픈(결제 활성화) 상태에서 /preorder 직링크는 /pay로 전환
  if (PAYMENT_ENABLED) redirect("/pay");

  const session = await auth();
  if (!session?.user?.id) redirect("/signin?from=/preorder");

  const supabase = getSupabaseAdmin();
  const { data: user } = supabase
    ? await supabase
        .from("users")
        .select("id, name, email, phone, marketing_consent, onboarded_at")
        .eq("id", session.user.id)
        .maybeSingle()
    : { data: null };

  if (supabase && !user) redirect("/signin?from=/preorder");
  if (supabase && user && !user.onboarded_at) redirect("/onboarding");

  // 이미 사전예약했으면 완료 페이지로
  if (supabase && user) {
    const { data: existing } = await supabase
      .from("applications")
      .select("id")
      .eq("user_id", user.id)
      .eq("cohort", "__COHORT__")
      .eq("is_preorder", true)
      .maybeSingle();
    if (existing) redirect("/preorder/done");
  }

  // ... render the pre-order card + <SurveyForm submitAction={submitPreorder} /> ...
  // (Layout/copy is brand-specific; rebuild per design.)
  return null;
}
```
