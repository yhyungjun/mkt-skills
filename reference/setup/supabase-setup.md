# Supabase 설정 절차

> DB 백엔드. env 키: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`(공개),
> `SUPABASE_SERVICE_ROLE_KEY`(서버 전용). 스키마는 `reference/db-schema.sql`.
> 외부 콘솔 UI 라벨은 자주 바뀌므로 "~ 찾기"로 기술 — 정확한 메뉴명은 화면에서 확인할 것.

## 1. 프로젝트 생성
1. https://supabase.com 로그인 → 대시보드에서 **New project** 찾기.
2. Organization 선택 → 프로젝트 이름·DB 비밀번호·리전(서울 `ap-northeast-2` 권장) 지정.
3. 생성 완료까지 1~2분 대기(프로비저닝).

## 2. URL / 키 발급 위치
1. 프로젝트 설정(Settings) → **API**(또는 "API Keys") 섹션 찾기.
2. 다음 3개를 복사해 `apps/web/.env`(또는 `.env.local`)에 넣는다:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
   - **anon / public 키** → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role 키**(secret 표시) → `SUPABASE_SERVICE_ROLE_KEY`
3. ⚠️ service_role 키는 모든 RLS를 우회한다. **서버 라우트/서버액션에서만** 사용, 클라이언트
   번들·Apps Script(`.gs`)에 절대 하드코딩 금지(원본 프로젝트 노출 전례 있음).

## 3. 마이그레이션 적용 (`reference/db-schema.sql`)
두 방법 중 택1.

**A. SQL Editor (가장 간단)**
1. 대시보드 좌측에서 **SQL Editor** 찾기 → New query.
2. `reference/db-schema.sql` 전체를 붙여넣고 Run.

**B. Supabase CLI (마이그레이션 관리)**
1. `supabase/migrations/` 아래에 `0001_init.sql` 등으로 스키마를 분리 저장.
2. `npx supabase link --project-ref <ref>` 로 원격 연결.
3. `npx supabase db push` 로 적용.
> 스키마는 6개 테이블(users / applications / payments / otp_codes / admins /
> email_sends + **email_events**)을 모두 생성한다. email_events 누락 전례 있으니
> 반드시 함께 생성됐는지 확인.

## 4. RLS 확인 (중요)
- 스키마는 **전 테이블 `enable row level security` + 정책 0개**다.
  → 정책이 없으면 anon 키로는 아무것도 못 읽고/못 쓴다(완전 차단). **service_role로만 접근**.
- 확인: 대시보드 → 각 테이블의 RLS 상태가 **Enabled**인지, 정책 목록이 **비어 있는지** 본다.
- 흔한 함정: "데이터가 안 읽힌다"의 99%는 클라이언트에서 anon 키로 직접 조회하려다 RLS에
  막힌 것. 이 스택은 **서버에서 service_role로 읽고 쓰는** 설계이므로 정상 동작이다.

## 5. 로컬 stub 모드 (env 미설정 시)
- env가 비어 있으면 Supabase 클라이언트 생성 함수가 **null을 반환하는 stub 모드**로 동작해
  빌드/개발 서버가 죽지 않는다(개발 초기 편의 패턴).
- 즉, DB 없이도 UI는 띄울 수 있으나 **실제 INSERT/조회는 동작하지 않는다.**
- 실데이터 흐름을 테스트하려면 위 3개 키를 반드시 채운다.

## 흔한 함정 요약
- service_role 키를 NEXT_PUBLIC_* 로 노출 → 즉시 키 로테이션.
- RLS Enabled인데 정책을 추가해버려 service_role 외 경로가 열림 → 의도와 다르면 정책 제거.
- 리전이 멀어 레이턴시 큼 → 한국 서비스면 서울 리전.
