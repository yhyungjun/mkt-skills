# `lib/auth.ts` — Auth.js v5 social-login template (snapshot)

> **출처:** granter-landing(`apps/web/lib/auth.ts`) 역설계 스냅샷.
> **이건 스냅샷 템플릿입니다. 라이브 레포를 참조하지 마세요** — 실제 운영 파일은 계속 바뀌므로,
> 새 프로젝트는 이 파일만 복사한 뒤 자기 레포 안에서 진화시킬 것.
>
> **교체 지점 (브랜드/도메인 placeholder — 그대로 두면 안 됨):**
> - `yourco.ai` → 실제 어드민 이메일 도메인 (env `ADMIN_DOMAIN`로도 주입 가능)
> - `@review.<BRAND>.local` 의 `<BRAND>` → 실제 브랜드 슬러그 (심사 계정 placeholder 이메일)
> - `getSupabaseAdmin` import 경로 → 실제 DB 어댑터 (Supabase가 아니면 같은 인터페이스로 교체)
> - `users` 테이블 컬럼명(`onboarded_at`, `marketing_consent`, `provider_id`, `phone_verified`) → 실제 스키마
> - `@/lib/signupConsent` → `auth-pages.md`의 동의쿠키 모듈
>
> **값 하드코딩 금지:** 모든 OAuth 키/시크릿은 env 변수 참조만(`process.env.*`). 값은 절대 코드에 박지 말 것.
>
> **이 템플릿의 핵심 가치(그대로 보존해야 하는 까다로운 로직):**
> 1. **Naver 커스텀 OAuth provider** — Auth.js 빌트인이 없어 OAuth 엔드포인트를 손으로 정의.
>    `userinfo` 응답이 `{ response: {...} }`로 한 겹 감싸져 옴 → `profile()`에서 `profile.response` 언랩.
> 2. **Kakao placeholder 이메일** — 비즈앱 전환 전 이메일 동의항목 권한이 없어 email이 `null` →
>    `kakao_{providerAccountId}@placeholder.local`로 임시 부여(전환 후 진짜 이메일로 마이그레이션 필요).
> 3. **동의쿠키로 신규가입 보호** — `/signin`에서 OAuth 시작한 신규 사용자는 약관 동의를 안 거쳤으므로
>    consent 쿠키가 없으면 INSERT 거부(`signIn` 콜백 `return false`) → `/signup`으로 유도.
> 4. **전화번호 정규화** — 카카오는 `+82 10-…` 형식 → `010-…`로 국가코드 치환. 네이버는 이미 `010-…`.
> 5. **toss-review Credentials** — PG(전자결제) 심사원용 ID/비번 로그인. 비밀번호는 bcrypt 해시를
>    base64로 감싸 env에 저장(`TOSS_REVIEW_PASSWORD_HASH_B64`), `bcrypt.compare`로 검증.

## 환경변수

```bash
# OAuth providers (값은 각 콘솔에서 발급 — 절대 코드에 하드코딩 금지)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
KAKAO_CLIENT_ID=
KAKAO_CLIENT_SECRET=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=

# Auth.js
AUTH_SECRET=            # openssl rand -base64 33

# 어드민 판별 (둘 중 하나라도 매칭되면 admin)
ADMIN_DOMAIN=yourco.ai          # 이 도메인 이메일은 전부 admin
ADMIN_EMAILS=                   # 콤마 구분 화이트리스트

# 카카오 비즈앱 + 이메일/전화 동의항목 검수 통과 후에만 true
OAUTH_REQUEST_CONTACT=false

# PG 심사용 Credentials 계정 (toss-review)
TOSS_REVIEW_ID=
TOSS_REVIEW_PASSWORD_HASH_B64=  # base64(bcrypt해시)  생성법은 아래 참고
```

심사 계정 해시 생성 예시:

```bash
# bcrypt 해시 → base64 (개행/특수문자 env 안전)
node -e "const b=require('bcryptjs');console.log(Buffer.from(b.hashSync(process.argv[1],10)).toString('base64'))" '심사용비밀번호'
```

## 코드

```ts
// lib/auth.ts
//
// 출처: granter-landing 역설계 스냅샷 템플릿. 라이브 레포 참조 금지 — 복사 후 자기 레포에서 진화.
// 교체 지점은 이 파일 상단 주석(.md) 참고: yourco.ai / <BRAND> / DB 어댑터 / 테이블 컬럼.
import NextAuth, { type DefaultSession, type NextAuthConfig } from "next-auth";
import Google from "next-auth/providers/google";
import Kakao, { type KakaoProfile } from "next-auth/providers/kakao";
import Credentials from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { getSupabaseAdmin } from "@/lib/supabase/server"; // ← 교체 지점: 실제 DB 어댑터
import { readSignupConsent, clearSignupConsent } from "@/lib/signupConsent";

const TOSS_REVIEW_PROVIDER_ID = "toss-review";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      role: "user" | "admin";
      provider?: string;
      onboarded: boolean;
    } & DefaultSession["user"];
  }
  interface User {
    phone?: string | null;
    onboarded?: boolean;
  }
}

/**
 * 전화번호를 한국 표준 형식(01012345678 → 010-1234-5678)으로 정규화.
 * 카카오는 "+82 10-1234-5678" 형식으로 오므로 국가코드 82를 0으로 치환.
 * 네이버는 이미 "010-1234-5678" 형식이라 그대로 통과.
 */
function normalizeKoreanPhone(raw: string | null | undefined): string | null {
  if (!raw) return null;
  let digits = raw.replace(/[^0-9]/g, "");
  if (digits.startsWith("82")) digits = "0" + digits.slice(2);
  if (digits.length === 11 && digits.startsWith("010")) {
    return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
  }
  return digits || null;
}

/**
 * 전화번호·이메일을 OAuth 필수 동의항목으로 요청할지 여부 (카카오).
 * 카카오 비즈앱 전환 + 동의항목(이메일/전화번호) 검수가 완료된 후에만 true로 켤 것.
 * 검수 전에 true면 카카오가 미등록 scope를 거부해 로그인 전체가 실패한다.
 */
const REQUEST_OAUTH_CONTACT = process.env.OAUTH_REQUEST_CONTACT === "true";

declare module "@auth/core/jwt" {
  interface JWT {
    role?: "user" | "admin";
    provider?: string;
    userId?: string;
    onboarded?: boolean;
  }
}

type NaverProfile = {
  resultcode: string;
  message: string;
  response: {
    id: string;
    email?: string;
    name?: string;
    nickname?: string;
    profile_image?: string;
    mobile?: string; // "010-1234-5678" — 동의항목 "휴대전화번호" 검수 통과 시 제공
    mobile_e164?: string; // "+821012345678"
  };
};

/**
 * 어드민 권한 판별 — 다음 중 하나라도 통과하면 admin:
 * 1) ADMIN_DOMAIN 환경변수와 이메일 도메인 일치 (예: @yourco.ai 전체)
 * 2) ADMIN_EMAILS 환경변수의 콤마 구분 화이트리스트에 포함
 */
export function isAdminEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const normalized = email.trim().toLowerCase();

  const adminDomain = process.env.ADMIN_DOMAIN?.trim().toLowerCase();
  if (adminDomain && normalized.endsWith("@" + adminDomain)) return true;

  const adminEmails = (process.env.ADMIN_EMAILS ?? "")
    .split(",")
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean);
  if (adminEmails.includes(normalized)) return true;

  return false;
}

/**
 * Naver 커스텀 OAuth provider.
 * Auth.js v5에 빌트인 Naver가 없어 OAuth 엔드포인트를 직접 정의한다.
 * userinfo 응답이 { resultcode, message, response: {...} } 형태로 한 겹 감싸져 오므로
 * profile()에서 profile.response를 언랩해야 한다 (← 까다로운 핵심 로직, 보존).
 */
const Naver = {
  id: "naver",
  name: "Naver",
  type: "oauth" as const,
  authorization: {
    url: "https://nid.naver.com/oauth2.0/authorize",
    params: { response_type: "code" },
  },
  token: "https://nid.naver.com/oauth2.0/token",
  userinfo: "https://openapi.naver.com/v1/nid/me",
  clientId: process.env.NAVER_CLIENT_ID,
  clientSecret: process.env.NAVER_CLIENT_SECRET,
  profile(profile: NaverProfile) {
    const r = profile.response;
    return {
      id: r.id,
      name: r.name ?? r.nickname ?? null,
      email: r.email ?? null,
      image: r.profile_image ?? null,
      phone: normalizeKoreanPhone(r.mobile ?? r.mobile_e164),
    };
  },
};

export const authConfig: NextAuthConfig = {
  trustHost: true,
  session: { strategy: "jwt" },
  pages: {
    signIn: "/signin",
    // signIn 콜백이 false 반환 시 /signin?error=AccessDenied로 보내, 우리가 만든 신규 가입자 유도 UI가 표시되게 함.
    // 미지정 시 기본값은 /api/auth/error 페이지.
    error: "/signin",
  },
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
    }),
    Kakao({
      clientId: process.env.KAKAO_CLIENT_ID,
      clientSecret: process.env.KAKAO_CLIENT_SECRET,
      // 검수 완료 후 OAUTH_REQUEST_CONTACT=true 로 켜면 이메일·전화번호를 필수 동의로 요청
      ...(REQUEST_OAUTH_CONTACT
        ? {
            authorization: {
              url: "https://kauth.kakao.com/oauth/authorize",
              params: {
                scope: "profile_nickname account_email phone_number name",
              },
            },
          }
        : {}),
      profile(profile: KakaoProfile) {
        const account = profile.kakao_account;
        return {
          id: profile.id.toString(),
          name: account?.profile?.nickname ?? null,
          email: account?.email ?? null,
          image: account?.profile?.profile_image_url ?? null,
          phone: normalizeKoreanPhone(account?.phone_number),
        };
      },
    }),
    Naver,
    // PG(전자결제) 심사원용 ID/비번 로그인. 소셜 가입 없이 보호 페이지에 들어갈 수 있게 하는 백도어.
    // 비밀번호는 bcrypt 해시를 base64로 감싸 env에 저장하고, 평문 입력을 bcrypt.compare로 검증.
    Credentials({
      id: TOSS_REVIEW_PROVIDER_ID,
      name: "심사용 계정",
      credentials: {
        username: { label: "ID", type: "text" },
        password: { label: "비밀번호", type: "password" },
      },
      async authorize(creds) {
        const expectedId = process.env.TOSS_REVIEW_ID;
        const hashB64 = process.env.TOSS_REVIEW_PASSWORD_HASH_B64;
        const expectedHash = hashB64
          ? Buffer.from(hashB64, "base64").toString("utf8")
          : null;
        if (!expectedId || !expectedHash) return null;
        const username = String(creds?.username ?? "");
        const password = String(creds?.password ?? "");
        if (username !== expectedId) return null;
        const ok = await bcrypt.compare(password, expectedHash);
        if (!ok) return null;
        return {
          id: "review-placeholder",
          email: `${expectedId}@review.<BRAND>.local`, // ← 교체 지점: <BRAND>
          name: "심사 계정",
        };
      },
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      // 소셜 로그인 사용자를 users 테이블에 동기화
      if (!account) return true;

      // 카카오는 비즈 앱 전환 전까지 이메일 동의항목 권한이 없어 email이 null로 옴.
      // providerId 기반 placeholder 이메일을 임시 부여 — 전환 후 진짜 이메일로 마이그레이션 필요.
      if (!user.email) {
        if (account.provider === "kakao" && account.providerAccountId) {
          user.email = `kakao_${account.providerAccountId}@placeholder.local`;
        } else {
          return false;
        }
      }

      const supabase = getSupabaseAdmin();
      if (!supabase) {
        // Stub mode — allow sign-in but skip DB sync (logged in console)
        console.warn("[auth.signIn] DB not configured. Skipping user sync for", user.email);
        return true;
      }

      const isReview = account.provider === TOSS_REVIEW_PROVIDER_ID;
      const provider = isReview
        ? null
        : (account.provider as "google" | "kakao" | "naver");
      const providerId = isReview ? null : String(account.providerAccountId ?? "");

      // OAuth provider가 전화번호를 제공한 경우에만 사용 (네이버·카카오, 동의항목 검수 통과 시).
      // 없으면(null) 신청 폼에서 입력한 기존 전화번호를 덮어쓰지 않는다.
      const phone = user.phone ?? null;

      // /signup 페이지에서 OAuth 시작 직전 저장된 약관·광고 동의값 (있으면).
      // 약관 동의가 있고 + 전화번호 prefill까지 받았으면 onboarded_at도 같이 채워서
      // 별도 /onboarding 단계를 생략한다.
      const consent = await readSignupConsent();
      const nowIso = new Date().toISOString();
      const canSkipOnboarding = !!(consent?.terms && phone);

      const { data: existing } = await supabase
        .from("users")
        .select("id, onboarded_at")
        .eq("email", user.email)
        .maybeSingle();

      // 신규 가입자 차단: /signin에서 OAuth 시작한 신규 사용자는 약관 동의를 거치지 않았으므로
      // INSERT 거부 → /signin?error=AccessDenied로 돌아가고, 안내 UI가 /signup으로 유도.
      // /signup을 통해 시작한 경우는 consent 쿠키가 있으므로 통과. 심사용 Credentials도 예외.
      if (!existing?.id && !consent && !isReview) {
        console.warn(
          "[auth.signIn] new user blocked — no consent cookie (must sign up via /signup):",
          user.email,
        );
        return false;
      }

      if (existing?.id) {
        user.id = existing.id;
        const willOnboard = existing.onboarded_at !== null || canSkipOnboarding;
        user.onboarded = willOnboard;

        const patch: Record<string, unknown> = {
          provider,
          provider_id: providerId,
        };
        // 이름은 사용자가 onboarding을 마치기 전까지만 OAuth 값으로 덮어씀.
        // onboarded_at이 있으면 사용자가 직접 수정한 이름일 수 있으므로 덮어쓰지 않음.
        if (!existing.onboarded_at && user.name) patch.name = user.name;
        if (phone) {
          patch.phone = phone;
          patch.phone_verified = true;
        }
        if (consent) patch.marketing_consent = consent.marketing;
        // 기존에 onboarded_at이 비어 있고 이번 가입에서 약관+전화 둘 다 갖춰지면 채움.
        if (canSkipOnboarding && !existing.onboarded_at) {
          patch.onboarded_at = nowIso;
        }
        await supabase.from("users").update(patch).eq("id", existing.id);
      } else {
        const insertRow: Record<string, unknown> = {
          email: user.email,
          name: user.name,
          phone,
          phone_verified: !!phone,
          provider,
          provider_id: providerId,
        };
        if (consent) insertRow.marketing_consent = consent.marketing;
        if (canSkipOnboarding) insertRow.onboarded_at = nowIso;

        const { data: created } = await supabase
          .from("users")
          .insert(insertRow)
          .select("id")
          .single();
        if (created?.id) user.id = created.id;
        user.onboarded = canSkipOnboarding;
      }

      // 동의 쿠키는 1회용 — 사용 후 즉시 삭제
      if (consent) await clearSignupConsent();
      return true;
    },
    async jwt({ token, user, account, trigger }) {
      if (user) {
        token.userId = user.id;
        // 어드민 권한의 단일 출처: 이메일 도메인 / 화이트리스트
        token.role = isAdminEmail(user.email) ? "admin" : "user";
        token.onboarded = user.onboarded ?? false;
      }
      if (account) {
        token.provider = account.provider;
      }
      // /onboarding 제출 후 update() 호출로 토큰을 강제 재발급할 때 onboarded_at을 다시 조회
      if (trigger === "update" && token.userId) {
        const supabase = getSupabaseAdmin();
        if (supabase) {
          const { data } = await supabase
            .from("users")
            .select("onboarded_at")
            .eq("id", token.userId)
            .maybeSingle();
          token.onboarded = data?.onboarded_at != null;
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = (token.userId as string) ?? "";
        session.user.role = token.role ?? "user";
        session.user.provider = token.provider;
        session.user.onboarded = token.onboarded ?? false;
      }
      return session;
    },
  },
};

export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);
```

## Provider별 주석 설명

| Provider | 빌트인? | 특이사항 |
|---|---|---|
| **Google** | O | 가장 단순. clientId/secret만. 전화번호 미제공 → onboarding에서 수집. |
| **Kakao** | O | 비즈앱 전환 전 email/phone 동의항목 권한 없음. `OAUTH_REQUEST_CONTACT` 플래그로 scope 토글. email null이면 `kakao_{id}@placeholder.local` 임시 부여. 전화는 `+82 10-` → `010-` 정규화. |
| **Naver** | **X (커스텀)** | OAuth 엔드포인트 직접 정의. `userinfo`가 `{ response: {...} }`로 감싸짐 → `profile.response` 언랩 필수. |
| **toss-review** | Credentials | PG 심사 백도어. bcrypt 해시(base64 인코딩 env) + `bcrypt.compare`. consent 쿠키 검사를 우회(`isReview` 예외). |

**의존성:** `next-auth@5` (beta/v5), `bcryptjs`. DB 어댑터는 `getSupabaseAdmin()`이
`null`이면 stub 모드(DB 동기화 스킵, 로그인은 허용)로 동작 — 로컬 개발 시 DB 없이도 흐름 확인 가능.
