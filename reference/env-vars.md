# 환경변수 마스터 목록 (강의 랜딩 풀스택)

> `apps/web/.env.example`로 떨어뜨려 시작. `NEXT_PUBLIC_*`는 브라우저 노출, 나머지는 서버 전용.
> Cloudflare 배포 시 public은 `wrangler.jsonc`의 `vars`, secret은 `wrangler secret put`.

```bash
# ── 사이트 ──
NEXT_PUBLIC_SITE_URL=http://localhost:3000        # 배포 도메인 (메타데이터 base)

# ── 결제 활성화 토글 (핵심 스위치) ──
NEXT_PUBLIC_PAYMENT_ENABLED=false                 # false → /preorder(사전예약), true → /pay(결제)

# ── YouTube 무료강의 ──
NEXT_PUBLIC_FREE_VIDEO_ID=                        # 사전예약 완료 후 노출용

# ── Google Tag Manager (GA4는 GTM 내부 태그로) ──
NEXT_PUBLIC_GTM_ID=                               # GTM-XXXXXXX (미설정 시 스크립트 미렌더)

# ── Supabase ──
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=                    # 공개키 (RLS로 보호)
SUPABASE_SERVICE_ROLE_KEY=                        # 서버 전용 (모든 DB 접근)

# ── Auth.js v5 (NextAuth) ──
AUTH_SECRET=                                      # openssl rand -base64 32
AUTH_URL=http://localhost:3000                    # OAuth redirect base
AUTH_TRUST_HOST=true                              # 프록시/엣지 환경

# ── OAuth Providers (3종) ──
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
KAKAO_CLIENT_ID=
KAKAO_CLIENT_SECRET=
OAUTH_REQUEST_CONTACT=false                       # true=카카오 이메일·전화 필수동의(비즈앱 검수 후)
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=

# ── Admin 권한 ──
ADMIN_DOMAIN=                                     # 이 이메일 도메인이면 자동 admin (예: yourco.ai)
ADMIN_EMAILS=                                     # 추가 화이트리스트 (콤마 구분)

# ── Toss Payments ──
TOSS_CLIENT_KEY=                                  # 브라우저에서 위젯 초기화 (공개)
TOSS_SECRET_KEY=                                  # 서버 결제승인 API (Basic 인증)

# ── Toss PG 심사용 임시계정 (Credentials provider) ──
TOSS_REVIEW_ID=
TOSS_REVIEW_PASSWORD_HASH_B64=                    # bcrypt 해시를 base64 인코딩

# ── SMS OTP 인증 (OCTOMO; 안 쓰면 생략 가능) ──
OCTOMO_API_KEY=

# ── 메일 발송 (Resend; 결제완료 메일) ──
RESEND_API_KEY=
```

## ⚠️ 시크릿 취급 주의
- **Supabase service_role / secret key를 `.gs`(Apps Script)나 클라이언트 코드에 절대 하드코딩 금지.**
  (원본 프로젝트에서 `send-preorder-email.gs`에 secret key가 노출된 전례 있음 → 반드시 환경/스크립트 속성으로.)
- `TOSS_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`는 서버 라우트/서버액션에서만.
- 키 로테이션: 노출 의심 시 즉시 재발급.
