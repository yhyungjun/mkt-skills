-- =============================================================================
-- 강의 랜딩 풀스택 — Supabase(PostgreSQL) 스키마 레퍼런스 (복붙용)
-- 원본: granter-landing/supabase/migrations/000{1,2,3}_*.sql 통합 + 보강
-- 적용: supabase/migrations/ 에 마이그레이션으로 넣거나 SQL Editor에서 실행.
-- 전 테이블 RLS 활성화 + 정책 없음 = service_role 만 접근(익명 차단). 서버에서만 읽고 쓴다.
-- =============================================================================

-- ── 1) users : 소셜로그인 회원 ──
create table public.users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  name text,
  phone text,                                   -- "010-1234-5678"
  phone_verified boolean default false,         -- SMS OTP 통과 여부
  provider text check (provider in ('google','kakao','naver')),
  provider_id text,
  marketing_consent boolean default false,
  onboarded_at timestamptz,                     -- /onboarding 완료 시각 (null이면 온보딩 미완료)
  created_at timestamptz default now()
);
alter table public.users enable row level security;

-- ── 2) applications : 강의 신청/사전예약 (+ 설문) ──
create table public.applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.users(id) on delete set null,
  name text not null,
  email text not null,
  phone text not null,
  marketing_consent boolean default false,
  cohort text default 'beta-2026',              -- 기수 코드
  status text check (status in ('pending','paid','cancelled','refunded')) default 'pending',
  is_preorder boolean default false,            -- true=사전예약자, false=결제자

  -- 설문 필드 (배열은 text[]) — 원본은 마이그레이션 없이 코드 INSERT로 동적 생성했으나,
  -- 재현 시 아래처럼 명시 선언 권장(스키마 드리프트 방지).
  survey_format text,                           -- 'online'|'offline'|'both'
  survey_days text[],
  survey_times text[],
  survey_region text,
  survey_status text,
  survey_channels text[],
  survey_revenue text,
  survey_granter text,
  survey_interests text[],
  survey_comment text,

  applied_at timestamptz default now()
);
alter table public.applications enable row level security;
create index applications_email_idx       on public.applications(email);
create index applications_status_idx      on public.applications(status);
create index applications_is_preorder_idx on public.applications(is_preorder);
create index applications_applied_at_idx  on public.applications(applied_at desc);

-- ── 3) payments : 토스 결제 기록 ──
create table public.payments (
  id uuid primary key default gen_random_uuid(),
  application_id uuid not null references public.applications(id) on delete cascade,
  toss_payment_key text unique,
  toss_order_id text unique not null,           -- ord-{app_id8}-{timestamp}
  amount integer not null,                      -- KRW
  tier text check (tier in ('earlybird-tier1','earlybird-tier2','regular')),
  status text check (status in ('ready','approved','failed','cancelled','refunded')) default 'ready',
  paid_at timestamptz,
  raw_response jsonb,                            -- 토스 승인 API 응답 원본
  created_at timestamptz default now()
);
alter table public.payments enable row level security;
create index payments_status_idx      on public.payments(status);
create index payments_application_idx on public.payments(application_id);

-- ── 4) otp_codes : SMS 인증 임시저장 ──
create table public.otp_codes (
  id uuid primary key default gen_random_uuid(),
  phone text not null,                          -- "01012345678" (하이픈 없음)
  code text not null,                           -- 4자리
  expires_at timestamptz not null,              -- 약 5분 TTL
  used boolean default false,
  created_at timestamptz default now()
);
alter table public.otp_codes enable row level security;
create index otp_codes_phone_idx on public.otp_codes(phone, used, expires_at);

-- ── 5) admins : 어드민 Credentials 로그인 (소셜과 분리) ──
create table public.admins (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  created_at timestamptz default now()
);
alter table public.admins enable row level security;

-- ── 6) email_sends / email_events : 메일 발송 + 오픈/클릭 추적 ──
-- ⚠️ 원본에서 email_events 가 트래킹 API는 참조하나 마이그레이션 누락된 전례 → 반드시 같이 생성.
create table public.email_sends (
  id uuid primary key default gen_random_uuid(),
  application_id uuid references public.applications(id) on delete set null,
  recipient_email text not null,
  recipient_name text,
  subject text not null,
  campaign text not null default 'preorder-2026',
  sent_at timestamptz default now()
);
alter table public.email_sends enable row level security;

create table public.email_events (
  id uuid primary key default gen_random_uuid(),
  email_send_id uuid references public.email_sends(id) on delete cascade,
  event_type text not null check (event_type in ('open','click')),
  metadata jsonb,                               -- click 시 { url }
  created_at timestamptz default now()
);
alter table public.email_events enable row level security;
create index email_events_send_id_idx on public.email_events(email_send_id);
