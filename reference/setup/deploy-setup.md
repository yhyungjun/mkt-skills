# 배포 설정 절차 (Cloudflare Workers / Vercel)

> 기본 배포: **Cloudflare Workers** (`@opennextjs/cloudflare`). Vercel도 가능.
> public env(`NEXT_PUBLIC_*`) → `wrangler.jsonc`의 `vars`.
> secret env → `wrangler secret put <KEY>`.
> 콘솔/CLI는 버전에 따라 다를 수 있으니 실제 출력으로 확인.

## A. Cloudflare Workers (@opennextjs/cloudflare)

### 1. 사전 준비
- 패키지: `@opennextjs/cloudflare`, `wrangler`.
- 설정 파일: `wrangler.jsonc`(name, account_id, compatibility_date, `nodejs_compat`,
  R2 assets, `vars`), `open-next.config.ts`, `next.config.ts`(`initOpenNextCloudflareForDev`).
- `npx wrangler login` 으로 계정 인증.

### 2. public env → `wrangler.jsonc` 의 `vars`
브라우저 노출 가능한 값만 `vars`에 평문으로 둔다:
```jsonc
{
  "vars": {
    "NEXT_PUBLIC_SITE_URL": "https://<도메인>",
    "NEXT_PUBLIC_PAYMENT_ENABLED": "false",
    "NEXT_PUBLIC_FREE_VIDEO_ID": "",
    "NEXT_PUBLIC_GTM_ID": "GTM-XXXXXXX",
    "NEXT_PUBLIC_SUPABASE_URL": "https://xxxx.supabase.co",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY": "<anon>",
    "AUTH_URL": "https://<도메인>",
    "AUTH_TRUST_HOST": "true"
  }
}
```
> `TOSS_CLIENT_KEY`는 공개키지만 운영 일관성을 위해 secret으로 넣어도 무방.

### 3. secret env → `wrangler secret put`
서버 전용 비밀값은 평문 보관 금지. 각각 실행(값은 프롬프트로 입력):
```bash
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
npx wrangler secret put AUTH_SECRET
npx wrangler secret put GOOGLE_CLIENT_ID
npx wrangler secret put GOOGLE_CLIENT_SECRET
npx wrangler secret put KAKAO_CLIENT_ID
npx wrangler secret put KAKAO_CLIENT_SECRET
npx wrangler secret put NAVER_CLIENT_ID
npx wrangler secret put NAVER_CLIENT_SECRET
npx wrangler secret put OAUTH_REQUEST_CONTACT
npx wrangler secret put ADMIN_DOMAIN
npx wrangler secret put ADMIN_EMAILS
npx wrangler secret put TOSS_CLIENT_KEY
npx wrangler secret put TOSS_SECRET_KEY
npx wrangler secret put TOSS_REVIEW_ID
npx wrangler secret put TOSS_REVIEW_PASSWORD_HASH_B64
npx wrangler secret put OCTOMO_API_KEY
npx wrangler secret put RESEND_API_KEY
```
> 안 쓰는 기능(OCTOMO 등) 키는 생략 가능. `OAUTH_REQUEST_CONTACT`/`ADMIN_*`는
> 비밀은 아니지만 secret로 넣어도 됨(또는 `vars`로).

### 4. 빌드 & 배포
```bash
npx opennextjs-cloudflare build
npx opennextjs-cloudflare deploy
```
> package.json 스크립트로 `preview`/`deploy`(= `opennextjs-cloudflare build && ... deploy`)
> 묶어두는 패턴 권장. 로컬 미리보기는 `preview` 사용.

---

## B. Vercel (대안)

### 1. 연결
```bash
npm i -g vercel
vercel login
vercel link            # 단일 프로젝트
# 모노레포(apps/web 등 하위 디렉터리)면:
vercel link --repo
```

### 2. env 등록
- 대시보드(Project → Settings → Environment Variables) 또는 CLI:
```bash
vercel env add SUPABASE_SERVICE_ROLE_KEY production
vercel env add AUTH_SECRET production
# ...필요한 키 전부 (public 포함). NEXT_PUBLIC_* 도 등록해야 빌드에 주입됨.
```
- Production / Preview / Development 환경별로 분리 등록.

### 3. 배포
```bash
vercel              # 프리뷰
vercel --prod       # 프로덕션
```

---

## 배포 후 점검 (공통)
- `AUTH_URL` / `NEXT_PUBLIC_SITE_URL` 이 실제 프로덕션 도메인인지.
- OAuth 콘솔 3종에 **프로덕션 redirect URI** 추가됐는지(`oauth-console-setup.md`).
- Toss **웹훅 URL** 등록 + 실키 교체 + `NEXT_PUBLIC_PAYMENT_ENABLED` 토글(`toss-setup.md`).
- Resend 도메인 **Verified** + 발신주소 정상(`resend-setup.md`).

## 흔한 함정 요약
- secret을 `wrangler.jsonc` `vars`에 평문으로 넣음 → 노출. 반드시 `wrangler secret put`.
- `NEXT_PUBLIC_*`를 빌드 시 주입 안 함(Vercel에서 env 누락) → 클라이언트에서 값 undefined.
- `nodejs_compat` 플래그 누락 → Cloudflare에서 일부 Node API 깨짐.
- 모노레포에서 `vercel link`로 단일 링크 → 잘못된 프로젝트. `vercel link --repo` 사용.
