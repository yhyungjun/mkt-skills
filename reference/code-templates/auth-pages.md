# Auth pages + consent cookie + route handler (snapshot)

> **출처:** granter-landing(`apps/web/app/signup/*`, `app/signin/page.tsx`,
> `app/api/auth/[...nextauth]/route.ts`, `lib/signupConsent.ts`,
> `components/ui/ReviewSignInForm.tsx`) 역설계 스냅샷.
> **이건 스냅샷 템플릿입니다. 라이브 레포를 참조하지 마세요** — 복사 후 자기 레포에서 진화시킬 것.
>
> **교체 지점 (브랜드/도메인 placeholder):**
> - signup `metadata.title` 의 `<BRAND> × <PARTNER>` → 실제 서비스명
> - SignupForm의 동의 문구(무료 자료 설명 등) → 실제 혜택/제품
> - `POST_ONBOARDING_PATH` (= 결제 전 `/preorder`, 결제 ON 시 `/pay`) → 실제 라우팅
> - `/apply`, `/onboarding`, `/preorder`, `/terms`, `/privacy` 경로 → 실제 경로
> - `@/components/ui/SocialIcons` → 실제 아이콘 컴포넌트
>
> **핵심 가치(보존):**
> - **동의쿠키 운반** — OAuth 외부 리다이렉트로 form data가 유실되므로, 약관·광고 동의값을
>   httpOnly 쿠키(TTL 5분)로 운반. `signIn` 콜백에서 1회 읽고 즉시 삭제.
> - **신규가입 보호 UX** — `/signin`에서 신규 사용자가 OAuth 시도 → 콜백 `false` →
>   `?error=AccessDenied` → 약관 동의 유도 UI로 `/signup` 안내.
> - **세션-DB 불일치 가드** — JWT는 있는데 users row가 없으면 보호 페이지 ↔ /signin 무한 루프 →
>   강제 로그아웃 UI.
> - **심사용 Credentials 폼** — `redirect:false`로 client-side 로그인 후 수동 이동.

---

## 1. `lib/signupConsent.ts` — 동의 httpOnly 쿠키

```ts
// lib/signupConsent.ts
//
// 출처: granter-landing 역설계 스냅샷 템플릿. 라이브 레포 참조 금지.
// OAuth 외부 리다이렉트로 form data가 유실되므로 약관/광고 동의값을 httpOnly 쿠키로 운반한다.
import "server-only";
import { cookies } from "next/headers";

/**
 * /signup 페이지에서 OAuth 시작 직전 약관·광고 동의값을 임시 저장하기 위한 쿠키.
 * OAuth 외부 리다이렉트를 거치며 form data가 유실되므로 httpOnly 쿠키로 운반.
 * signIn 콜백에서 한 번 읽고 즉시 삭제 (TTL 5분).
 */
export const SIGNUP_CONSENT_COOKIE = "signup_consent";
const TTL_SECONDS = 5 * 60;

export type SignupConsent = {
  terms: boolean;
  marketing: boolean;
};

export async function writeSignupConsent(consent: SignupConsent): Promise<void> {
  const store = await cookies();
  store.set(SIGNUP_CONSENT_COOKIE, JSON.stringify(consent), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    maxAge: TTL_SECONDS,
    path: "/",
  });
}

export async function readSignupConsent(): Promise<SignupConsent | null> {
  const store = await cookies();
  const raw = store.get(SIGNUP_CONSENT_COOKIE)?.value;
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<SignupConsent>;
    if (typeof parsed.terms !== "boolean" || typeof parsed.marketing !== "boolean") {
      return null;
    }
    return { terms: parsed.terms, marketing: parsed.marketing };
  } catch {
    return null;
  }
}

export async function clearSignupConsent(): Promise<void> {
  const store = await cookies();
  store.delete(SIGNUP_CONSENT_COOKIE);
}
```

---

## 2. `app/api/auth/[...nextauth]/route.ts` — route handler

```ts
// app/api/auth/[...nextauth]/route.ts
// 출처: granter-landing 역설계 스냅샷 템플릿. Auth.js v5는 handlers를 그대로 GET/POST로 export.
import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;
```

---

## 3. `app/signup/page.tsx` — 회원가입 (서버 컴포넌트 + Server Action)

```tsx
// app/signup/page.tsx
//
// 출처: granter-landing 역설계 스냅샷 템플릿. 라이브 레포 참조 금지.
// 교체 지점: metadata.title, POST_ONBOARDING_PATH, /terms·/privacy 경로.
import { signIn, auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { writeSignupConsent } from "@/lib/signupConsent";
import { POST_ONBOARDING_PATH } from "@/lib/config";
import { SignupForm } from "./SignupForm";

export const metadata = {
  title: "회원가입 | <BRAND> × <PARTNER>", // ← 교체 지점
};

async function signupWith(formData: FormData) {
  "use server";
  const provider = String(formData.get("provider") ?? "");
  const terms = formData.get("terms_consent") === "true";
  const marketing = formData.get("marketing_consent") === "true";

  if (!["google", "kakao", "naver"].includes(provider)) return;
  // 약관 미동의면 OAuth 시작 자체를 차단
  if (!terms) return;

  // ★ 핵심: 동의값을 httpOnly 쿠키로 저장 → OAuth 리다이렉트 후 signIn 콜백에서 읽음.
  await writeSignupConsent({ terms, marketing });
  // 로그인 후 목적지는 POST_ONBOARDING_PATH(미결제=/preorder). 온보딩 필요 여부는
  // /preorder의 `!onboarded_at → /onboarding` 가드가 단일 기준으로 판단한다.
  // → 전화번호가 있으면(카카오·네이버, 동의항목 검수 통과 시) onboarded_at이 채워져 온보딩을 건너뛰고,
  //   없으면(구글·검수 전) 온보딩에서 전화번호를 수집한다.
  await signIn(provider, { redirectTo: POST_ONBOARDING_PATH });
}

export default async function SignupPage() {
  const session = await auth();
  if (session?.user) redirect(POST_ONBOARDING_PATH);

  return (
    <main className="signin-wrap">
      <section className="signin-card">
        <p className="meta">회원가입</p>
        <h1>3초 안에 시작하기</h1>
        <p className="signin-sub">
          소셜 계정으로 가입한 뒤, 정식 오픈 시 우선 결제 안내를 받아보세요.
        </p>

        <SignupForm signupWith={signupWith} />

        <p className="signin-foot meta">
          이미 가입하셨나요? <Link href="/signin">로그인 →</Link>
        </p>
        <p className="signin-foot meta">
          <Link href="/">← 홈으로 돌아가기</Link>
        </p>
      </section>
    </main>
  );
}
```

---

## 4. `app/signup/SignupForm.tsx` — 동의 체크박스 + 소셜 버튼 (client)

```tsx
// app/signup/SignupForm.tsx
//
// 출처: granter-landing 역설계 스냅샷 템플릿. 라이브 레포 참조 금지.
// 약관 동의(필수)·마케팅(선택) 체크 상태를 form data에 실어 Server Action으로 전달.
// 약관 미동의 시 소셜 버튼 disabled.
"use client";

import { useState } from "react";
import Link from "next/link";
import { KakaoIcon, NaverIcon, GoogleIcon } from "@/components/ui/SocialIcons";

type Provider = "google" | "kakao" | "naver";

type SignupFormProps = {
  signupWith: (formData: FormData) => void;
};

export function SignupForm({ signupWith }: SignupFormProps) {
  const [terms, setTerms] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const allChecked = terms && marketing;

  function toggleAll(checked: boolean) {
    setTerms(checked);
    setMarketing(checked);
  }

  function buildAction(provider: Provider) {
    return (formData: FormData) => {
      formData.set("provider", provider);
      formData.set("terms_consent", terms ? "true" : "false");
      formData.set("marketing_consent", marketing ? "true" : "false");
      signupWith(formData);
    };
  }

  return (
    <>
      <fieldset className="signup-consents">
        <label className="consent consent-all">
          <input
            type="checkbox"
            checked={allChecked}
            onChange={(e) => toggleAll(e.target.checked)}
          />
          <strong>전체 동의</strong>
        </label>

        <hr className="consent-divider" />

        <label className="consent">
          <input
            type="checkbox"
            checked={terms}
            onChange={(e) => setTerms(e.target.checked)}
          />
          <span>
            <Link href="/terms" target="_blank" rel="noopener noreferrer">
              이용약관
            </Link>
            ·
            <Link href="/privacy" target="_blank" rel="noopener noreferrer">
              개인정보 처리방침
            </Link>
            에 동의합니다 (필수)
          </span>
        </label>

        <div className="consent-row">
          <label className="consent">
            <input
              type="checkbox"
              checked={marketing}
              onChange={(e) => setMarketing(e.target.checked)}
            />
            <span>결제 안내·강의 소식 수신에 동의합니다 (선택)</span>
          </label>
          {/* ← 교체 지점: 아래 혜택 설명은 브랜드별로 교체 */}
          <details className="consent-help">
            <summary aria-label="자세히 보기">i</summary>
            <p className="consent-help-pop">
              <strong>사전예약 한정 무료 자료</strong>를 보내드립니다.
              <br />
              정규 소식이 함께 담겨 광고성 정보로 분류되기 때문에, 수신에 동의해주신 분께만 발송 가능합니다.
            </p>
          </details>
        </div>
      </fieldset>

      <div className="signin-buttons">
        <form action={buildAction("kakao")}>
          <button type="submit" className="btn btn-kakao" disabled={!terms}>
            <KakaoIcon />카카오로 가입하기
          </button>
        </form>
        <form action={buildAction("naver")}>
          <button type="submit" className="btn btn-naver" disabled={!terms}>
            <NaverIcon />네이버로 가입하기
          </button>
        </form>
        <form action={buildAction("google")}>
          <button type="submit" className="btn btn-google" disabled={!terms}>
            <GoogleIcon />Google로 가입하기
          </button>
        </form>
      </div>
    </>
  );
}
```

---

## 5. `app/signin/page.tsx` — 로그인 + 신규가입 유도 + 세션 가드

```tsx
// app/signin/page.tsx
//
// 출처: granter-landing 역설계 스냅샷 템플릿. 라이브 레포 참조 금지.
// 핵심: (a) AccessDenied → 신규가입 유도, (b) 세션-DB 불일치 → 강제 로그아웃, (c) 심사용 폼.
import { signIn, signOut, auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { ReviewSignInForm } from "@/components/ui/ReviewSignInForm";
import { KakaoIcon, NaverIcon, GoogleIcon } from "@/components/ui/SocialIcons";
import { POST_ONBOARDING_PATH } from "@/lib/config";
import { getSupabaseAdmin } from "@/lib/supabase/server"; // ← 교체 지점: 실제 DB 어댑터

async function signInWith(formData: FormData) {
  "use server";
  const provider = String(formData.get("provider") ?? "");
  if (!["google", "kakao", "naver"].includes(provider)) return;
  await signIn(provider, { redirectTo: POST_ONBOARDING_PATH });
}

async function forceSignOutAction() {
  "use server";
  await signOut({ redirectTo: "/signup" });
}

export default async function SignInPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; error?: string }>;
}) {
  const session = await auth();
  const { from, error } = await searchParams;

  // 신규 가입자가 /signin에서 OAuth를 시도하면 signIn 콜백이 false 반환 →
  // /signin?error=AccessDenied 로 돌아옴. 약관 동의를 받기 위해 /signup으로 유도.
  if (!session?.user?.id && error === "AccessDenied") {
    return (
      <main className="signin-wrap">
        <section className="signin-card">
          <p className="meta">SIGN UP · 약관 동의 필요</p>
          <h1>처음 오신 걸 환영합니다.</h1>
          <p className="signin-sub">
            가입 시 이용약관·개인정보 처리방침 동의가 필요합니다. 회원가입 페이지에서 약관에 동의하신 후 다시 시도해주세요.
          </p>
          <Link href="/signup" className="btn btn-primary signin-newuser-cta">
            회원가입 페이지로 →
          </Link>
          <p className="signin-foot meta">
            <Link href="/">← 홈으로 돌아가기</Link>
          </p>
        </section>
      </main>
    );
  }

  if (session?.user?.id) {
    // 세션-DB 불일치 가드: JWT는 있지만 users 테이블에 매칭 row가 없으면
    // /preorder 같은 보호 페이지가 /signin으로 다시 보내 무한 루프 발생.
    // 이 경우 강제 로그아웃 + /signup 안내.
    const supabase = getSupabaseAdmin();
    const dbUser = supabase
      ? (
          await supabase
            .from("users")
            .select("id")
            .eq("id", session.user.id)
            .maybeSingle()
        ).data
      : { id: "stub" as const };

    if (supabase && !dbUser) {
      console.warn("[signin] Session/DB mismatch — userId not in users:", session.user.id);
      return (
        <main className="signin-wrap">
          <section className="signin-card">
            <p className="meta">SESSION · 만료</p>
            <h1>세션을 다시 시작해주세요.</h1>
            <p className="signin-sub">
              저장된 로그인 정보가 현재 계정 정보와 일치하지 않습니다.
              아래 버튼으로 로그아웃 후 다시 로그인해주세요.
            </p>
            <form action={forceSignOutAction}>
              <button type="submit" className="btn btn-primary">
                로그아웃 후 다시 시작 →
              </button>
            </form>
            <p className="signin-foot meta">
              <Link href="/">← 홈으로 돌아가기</Link>
            </p>
          </section>
        </main>
      );
    }

    redirect(from ?? POST_ONBOARDING_PATH);
  }

  return (
    <main className="signin-wrap">
      <section className="signin-card">
        <p className="meta">로그인</p>
        <h1>다시 오신 걸 환영합니다.</h1>
        <p className="signin-sub">
          기존에 가입한 소셜 계정으로 로그인하세요.
        </p>
        <div className="signin-buttons">
          <form action={signInWith}>
            <input type="hidden" name="provider" value="kakao" />
            <button type="submit" className="btn btn-kakao">
              <KakaoIcon />카카오로 계속하기
            </button>
          </form>
          <form action={signInWith}>
            <input type="hidden" name="provider" value="naver" />
            <button type="submit" className="btn btn-naver">
              <NaverIcon />네이버로 계속하기
            </button>
          </form>
          <form action={signInWith}>
            <input type="hidden" name="provider" value="google" />
            <button type="submit" className="btn btn-google">
              <GoogleIcon />Google로 계속하기
            </button>
          </form>
        </div>

        {/* PG 심사 전용 — 출시 후에는 제거하거나 env 플래그로 숨길 것 */}
        <details className="signin-review">
          <summary>심사용 계정 로그인 (PG 심사 전용)</summary>
          <ReviewSignInForm />
        </details>

        <p className="signin-foot meta">
          처음이신가요? <Link href="/signup">회원가입 →</Link>
        </p>
        <p className="signin-foot meta">
          <Link href="/">← 홈으로 돌아가기</Link>
        </p>
      </section>
    </main>
  );
}
```

---

## 6. `components/ui/ReviewSignInForm.tsx` — 심사용 Credentials 폼 (client)

```tsx
// components/ui/ReviewSignInForm.tsx
//
// 출처: granter-landing 역설계 스냅샷 템플릿. 라이브 레포 참조 금지.
// toss-review Credentials provider로 client-side 로그인(redirect:false) 후 수동 이동.
// 교체 지점: 성공 후 이동 경로 "/apply".
"use client";

import { signIn } from "next-auth/react";
import { useState, type FormEvent } from "react";

export function ReviewSignInForm() {
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const form = e.currentTarget;
    const data = new FormData(form);
    const username = String(data.get("username") ?? "");
    const password = String(data.get("password") ?? "");

    const result = await signIn("toss-review", {
      username,
      password,
      redirect: false,
    });

    if (result?.error) {
      setError("ID 또는 비밀번호가 올바르지 않습니다.");
      setSubmitting(false);
      return;
    }
    window.location.href = "/apply"; // ← 교체 지점
  };

  return (
    <form onSubmit={onSubmit} className="signup-form">
      <label>
        ID
        <input
          type="text"
          name="username"
          required
          autoComplete="off"
          spellCheck={false}
          placeholder="제공된 심사용 ID 입력"
        />
      </label>
      <label>
        비밀번호
        <input
          type="password"
          name="password"
          required
          autoComplete="new-password"
          placeholder="제공된 심사용 비밀번호 입력"
        />
      </label>
      {error && <p className="form-status error">{error}</p>}
      <button type="submit" className="btn btn-secondary" disabled={submitting}>
        {submitting ? "확인 중..." : "로그인"}
      </button>
    </form>
  );
}
```

---

## 보조: `lib/config.ts` 의 `POST_ONBOARDING_PATH`

이 템플릿이 의존하는 라우팅 상수. 결제 토글에 따라 목적지가 바뀐다.

```ts
// 결제 ON이면 /pay, 아직 사전예약 단계면 /preorder
export const POST_ONBOARDING_PATH = PAYMENT_ENABLED ? "/pay" : "/preorder";
```

## 전체 흐름 요약

```
/signup
  └ 약관(필수)·마케팅(선택) 체크 → 소셜 버튼 클릭
     └ Server Action: writeSignupConsent(쿠키) → signIn(provider, redirectTo)
        └ OAuth 외부 리다이렉트 (form data 유실, but 쿠키는 살아있음)
           └ signIn 콜백: readSignupConsent → users upsert → clearSignupConsent
              └ redirectTo (POST_ONBOARDING_PATH)

/signin (기존 사용자용)
  ├ 신규가 OAuth 시도 → 콜백 false → ?error=AccessDenied → "회원가입 페이지로" 유도
  ├ 세션 O + DB row X → 강제 로그아웃 UI
  └ 심사용 폼(details) → toss-review Credentials → /apply
```
