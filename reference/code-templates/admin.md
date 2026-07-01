# Admin (P10) — 대시보드·차트·날짜선택·트래픽·신청자·가입자

> granter-landing `/admin/*` 역설계 스냅샷. **복붙 후 placeholder만 교체하면 동작.**
> 의존성: P4 DB(`getSupabaseAdmin`)·P9 인증(`auth`/`isAdminEmail` role) · 트래픽은 P8 트래킹(GA4) + `lib/sections.ts`.
>
> 구성: 다크 상단 네비 + 4탭(**대시보드 · 신청자 · 가입자 · 트래픽**). 모든 페이지는
> `force-dynamic` + role 가드. 4페이지가 **하나의 기간 선택 UI(`RangePicker`)를 공유**한다.

```
app/admin/
  layout.tsx                  다크 네비 + 탭 + 로그아웃(서버액션). role!=admin이면 탭 숨김
  signin/page.tsx             Google OAuth 전용. 비-어드민이면 denied 안내
  page.tsx                    대시보드 — 통계카드·전환율·채널분포·설문(Recharts)
  RangePicker.tsx             공용 기간 드롭다운(프리셋 + 맞춤날짜)  ← 4페이지 공유
  SurveyDashboard.tsx         설문 Pie/Bar/Area (대시보드 하위)
  applications/page.tsx       신청자 표 + 필터 + CSV
  applications/SurveyDetail.tsx  신청자 행 펼침(설문 상세)
  applications/export.csv/route.ts
  users/page.tsx              가입자 표 + 필터 + CSV
  users/export.csv/route.ts
  traffic/page.tsx            트래픽(GA4) — 자체 기간선택(프리셋 7/28/90)
  traffic/TrafficCharts.tsx   GA4 차트(Pie·Area·Bar·SVG퍼널·히트맵)
lib/
  adminRange.ts               공용 기간 해석기(resolveRange)  ← 대시보드/신청자/가입자 공유
  ga4.ts                      GA4 Data API 페처(server-only)
```

> ⚠️ **제품별 교체 지점**(하드코딩 금지 — 상품마다 다름):
> - `survey_*` 컬럼·라벨·집계 항목 = granter 설문 전용 → 상품 설문에 맞게 교체.
> - 플로우 퍼널 경로(`/signup`·`/preorder`·`/preorder/done`)·`login` 이벤트 → 실제 라우트/이벤트로.
> - `LANDING_SECTIONS`(P8 `lib/sections.ts`)가 섹션 퍼널을 구동.
> - 색 팔레트: **트래픽은 브랜드 토큰(`SIGNAL`)**, 대시보드 설문은 범용 팔레트 → 가능하면 브랜드색으로 통일.
> - `SEATS.earlybirdTotal`(config), `ADMIN_DOMAIN`/`ADMIN_EMAILS`(인증).

---

## 1. 레이아웃 · 인증 가드 · 로그인

### `app/admin/layout.tsx`
다크 네비 + 탭. 탭은 `role === "admin"`일 때만 노출. 로그아웃은 서버액션.

```tsx
import { auth, signOut } from "@/lib/auth";
import Link from "next/link";

async function adminSignOut() {
  "use server";
  await signOut({ redirectTo: "/admin/signin" });
}

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const session = await auth();
  // 미인증 트래픽은 proxy.ts가 이미 /admin/signin으로 보냄. 탭 노출만 role로 가드.
  return (
    <>
      <header className="admin-nav">
        <div className="wrap admin-nav-inner">
          <Link href="/admin" className="admin-logo">GRANTER ADMIN</Link>
          {session?.user?.role === "admin" && (
            <nav className="admin-tabs">
              <Link href="/admin">대시보드</Link>
              <Link href="/admin/applications">신청자</Link>
              <Link href="/admin/users">가입자</Link>
              <Link href="/admin/traffic">트래픽</Link>
              <form action={adminSignOut} style={{ display: "inline" }}>
                <button type="submit" className="btn-link">로그아웃</button>
              </form>
            </nav>
          )}
        </div>
      </header>
      <main className="admin-main"><div className="wrap">{children}</div></main>
    </>
  );
}
```

### 페이지 가드 (모든 admin 페이지/라우트 공통)
페이지 컴포넌트 맨 앞 + CSV 라우트에 동일 패턴. **이중 방어**(proxy + 페이지).

```tsx
export const dynamic = "force-dynamic";   // 통계는 항상 최신 — 캐시 금지

const session = await auth();
if (session?.user?.role !== "admin") redirect("/admin/signin");
// CSV 라우트는: return NextResponse.json({ error: "unauthorized" }, { status: 401 });
```

### `app/admin/signin/page.tsx`
Google OAuth 전용. 로그인했지만 어드민 아님 → `denied` 안내(권한 요청 유도).

```tsx
import { signIn, auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";

async function signInWithGoogle(formData: FormData) {
  "use server";
  const from = String(formData.get("from") ?? "/admin");
  await signIn("google", { redirectTo: from });
}

export default async function AdminSignInPage({
  searchParams,
}: { searchParams: Promise<{ from?: string; error?: string }> }) {
  const { from = "/admin", error } = await searchParams;
  const session = await auth();
  if (session?.user?.role === "admin") redirect(from);
  const denied = Boolean(session?.user); // 로그인했는데 여기 도달 = 권한 없음

  return (
    <main className="signin-wrap">
      <section className="signin-card">
        <p className="meta">ADMIN · 로그인</p>
        <h1>운영자 로그인</h1>
        <p className="signin-sub">허용된 워크스페이스 이메일만 접근할 수 있습니다. Google 계정으로 로그인해 주세요.</p>
        {denied && (
          <p className="form-status error">
            <strong>{session?.user?.email ?? "이 계정"}</strong>은 어드민 권한이 없는 계정입니다.
          </p>
        )}
        {error === "AccessDenied" && <p className="form-status error">권한이 없는 계정입니다.</p>}
        <form action={signInWithGoogle}>
          <input type="hidden" name="from" value={from} />
          <button type="submit" className="btn btn-google"><span>G</span> Google로 로그인</button>
        </form>
        <p className="signin-foot meta"><Link href="/">← 랜딩</Link></p>
      </section>
    </main>
  );
}
```

---

## 2. 날짜선택 (공용) — `lib/adminRange.ts` + `RangePicker.tsx`

**핵심 패턴**: 대시보드·신청자·가입자가 **같은 `resolveRange`로 기간을 해석**하고 같은 `RangePicker` UI를 쓴다.
`searchParams`의 `days`(all/7/28/90) 또는 `from~to`(맞춤)를 받아 **DB 필터용 ISO + 표시 라벨**로 환원.
타임존은 **KST(`Asia/Seoul`)** 고정. `extra`로 `q`/`status` 등 다른 쿼리를 보존한다.

> ⚠️ **트래픽 페이지는 예외** — GA4가 `"28daysAgo"`/`"yesterday"` 같은 상대 날짜 문자열을 요구하고
> "전체" 개념이 없어, `traffic/page.tsx`는 같은 `.range-*` UI를 쓰되 **자체 인라인 해석기**(프리셋 7/28/90, 기본 28)를 둔다. §5 참조.

### `lib/adminRange.ts`
```ts
// 어드민 공용 날짜 범위 — 대시보드·가입자·신청자가 동일한 기간 선택을 공유한다.
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export const RANGE_PRESETS = [
  { key: "all", label: "전체" },
  { key: "7", label: "지난 7일" },
  { key: "28", label: "지난 28일" },
  { key: "90", label: "지난 90일" },
] as const;

export type ResolvedRange = {
  isCustom: boolean;
  preset: string;            // "all" | "7" | "28" | "90" | "custom"
  from?: string; to?: string;
  startISO: string | null;   // null = 필터 없음(전체)
  endISO: string | null;
  topLabel: string;          // 드롭다운 제목 ("전체 기간" 등)
  rangeHuman: string;        // 사람이 읽는 기간 ("6월 1일 ~ 2026년 6월 14일")
};

function addDays(d: Date, n: number): Date { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
function fmtK(d: Date, withYear: boolean): string {
  return d.toLocaleDateString("ko-KR", {
    timeZone: "Asia/Seoul",
    ...(withYear ? { year: "numeric" as const } : {}),
    month: "long", day: "numeric",
  });
}

/** searchParams → 해석된 범위. defaultPreset: 값 없을 때 기본(목록/대시보드는 "all"). */
export function resolveRange(
  sp: { days?: string; from?: string; to?: string },
  defaultPreset: string = "all",
): ResolvedRange {
  const isCustom = !!sp.from && !!sp.to && DATE_RE.test(sp.from) && DATE_RE.test(sp.to) && sp.from <= sp.to;
  if (isCustom) {
    const startISO = new Date(`${sp.from}T00:00:00+09:00`).toISOString();
    const endISO = new Date(`${sp.to}T23:59:59.999+09:00`).toISOString();
    return { isCustom: true, preset: "custom", from: sp.from, to: sp.to, startISO, endISO,
      topLabel: "맞춤 기간", rangeHuman: `${fmtK(new Date(startISO), false)} ~ ${fmtK(new Date(endISO), true)}` };
  }
  const preset = ["all", "7", "28", "90"].includes(sp.days ?? "") ? (sp.days as string) : defaultPreset;
  if (preset === "all")
    return { isCustom: false, preset: "all", startISO: null, endISO: null, topLabel: "전체 기간", rangeHuman: "모든 기간" };
  const n = Number(preset);
  const now = new Date();
  const startD = addDays(now, -n);
  return { isCustom: false, preset, startISO: startD.toISOString(), endISO: now.toISOString(),
    topLabel: `지난 ${n}일`, rangeHuman: `${fmtK(startD, false)} ~ ${fmtK(now, true)}` };
}
```

### `app/admin/RangePicker.tsx`
순수 `<details>` 드롭다운(JS 없음). 프리셋 링크 + 맞춤 날짜 GET 폼. `extra`로 기존 필터 쿼리 보존.

```tsx
import Link from "next/link";
import { RANGE_PRESETS, type ResolvedRange } from "@/lib/adminRange";

export function RangePicker({
  basePath, range, extra = {},
}: { basePath: string; range: ResolvedRange; extra?: Record<string, string> }) {
  const extraEntries = Object.entries(extra).filter(([, v]) => v);
  const extraQs = extraEntries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
  const presetHref = (key: string) => {
    const parts = [`days=${key}`];
    if (extraQs) parts.push(extraQs);
    return `${basePath}?${parts.join("&")}`;
  };
  return (
    <details className="range-dd">
      <summary className="range-trigger">
        <span className="range-text">
          <span className="range-label">{range.topLabel}</span>
          <span className="range-value">{range.rangeHuman}</span>
        </span>
        <span className="range-caret" aria-hidden="true">▾</span>
      </summary>
      <div className="range-menu">
        <div className="range-presets">
          {RANGE_PRESETS.map((p) => (
            <Link key={p.key} href={presetHref(p.key)}
              className={!range.isCustom && range.preset === p.key ? "active" : ""}>{p.label}</Link>
          ))}
        </div>
        <form method="get" action={basePath} className="range-form">
          {extraEntries.map(([k, v]) => <input key={k} type="hidden" name={k} value={v} />)}
          <div className="range-fields">
            <input type="date" name="from" defaultValue={range.from ?? ""} aria-label="시작일" required />
            <span className="range-sep">~</span>
            <input type="date" name="to" defaultValue={range.to ?? ""} aria-label="종료일" required />
          </div>
          <button type="submit">조회</button>
        </form>
      </div>
    </details>
  );
}
```

**사용** (페이지 헤더):
```tsx
const range = resolveRange({ days, from, to });          // 대시보드/신청자/가입자
<RangePicker basePath="/admin/applications" range={range} extra={{ q, status, type }} />
```

---

## 3. 대시보드 — `app/admin/page.tsx`

서버에서 Supabase 카운트 집계 → 통계카드 4개(가입자·신청자·결제완료·전환율) + 채널분포 막대 + 설문 차트.
카운트는 `head: true, count: "exact"`로 행 안 가져오고 카운트만. `byApplied`로 기간 필터 일괄 적용.
**관리자 계정은 가입자 수에서 제외**(`isAdminEmail`). 전환율 = 결제완료/신청자.

```tsx
import { auth, isAdminEmail } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import { SEATS } from "@/lib/config";
import { resolveRange } from "@/lib/adminRange";
import { RangePicker } from "./RangePicker";
import { SurveyDashboard } from "./SurveyDashboard";

export const dynamic = "force-dynamic";

type CountItem = { label: string; count: number };
type SurveyStats = {
  total: number;
  format: CountItem[]; days: CountItem[]; times: CountItem[]; region: CountItem[];
  status: CountItem[]; channels: CountItem[]; revenue: CountItem[]; granter: CountItem[]; interests: CountItem[];
  daily: { date: string; count: number }[];
};
type Stats = {
  users: number; admins: number; applications: number; preorders: number; payments: number;
  pending: number; paid: number; providers: { provider: string; count: number }[]; survey: SurveyStats | null;
};

async function loadStats(startISO: string | null, endISO: string | null): Promise<Stats | null> {
  const supabase = getSupabaseAdmin();
  if (!supabase) return null;

  // 신청(applied_at) / 가입(created_at)에 기간 필터 적용
  function byApplied<T extends { gte(c: string, v: string): T; lte(c: string, v: string): T }>(qb: T): T {
    let x = qb;
    if (startISO) x = x.gte("applied_at", startISO);
    if (endISO) x = x.lte("applied_at", endISO);
    return x;
  }
  let usersQuery = supabase.from("users").select("email, provider");
  if (startISO) usersQuery = usersQuery.gte("created_at", startISO);
  if (endISO) usersQuery = usersQuery.lte("created_at", endISO);

  const [allUsersRes, applications, preorders, payments, pending, paid] = await Promise.all([
    usersQuery,
    byApplied(supabase.from("applications").select("id", { count: "exact", head: true })),
    byApplied(supabase.from("applications").select("id", { count: "exact", head: true }).eq("is_preorder", true)),
    byApplied(supabase.from("applications").select("id", { count: "exact", head: true }).eq("is_preorder", false)),
    byApplied(supabase.from("applications").select("id", { count: "exact", head: true }).eq("is_preorder", false).eq("status", "pending")),
    byApplied(supabase.from("applications").select("id", { count: "exact", head: true }).eq("status", "paid")),
  ]);

  const allUsers = allUsersRes.data ?? [];
  const regularUsers = allUsers.filter((u) => !isAdminEmail(u.email));
  const adminCount = allUsers.length - regularUsers.length;

  const providerMap = new Map<string, number>();
  for (const row of regularUsers) {
    const key = row.provider ?? "직접가입";
    providerMap.set(key, (providerMap.get(key) ?? 0) + 1);
  }
  const providers = Array.from(providerMap.entries())
    .map(([provider, count]) => ({ provider, count })).sort((a, b) => b.count - a.count);

  // 설문 통계 — 사전예약 + survey_format 있는 행만 (제품별 컬럼 교체)
  let surveyQuery = supabase.from("applications")
    .select("applied_at, survey_format, survey_days, survey_times, survey_region, survey_status, survey_channels, survey_revenue, survey_granter, survey_interests")
    .eq("is_preorder", true).not("survey_format", "is", null);
  if (startISO) surveyQuery = surveyQuery.gte("applied_at", startISO);
  if (endISO) surveyQuery = surveyQuery.lte("applied_at", endISO);
  const { data: surveyRows } = await surveyQuery;

  let survey: SurveyStats | null = null;
  if (surveyRows && surveyRows.length > 0) {
    // 단일 선택 컬럼 집계
    function countSingle(rows: Record<string, unknown>[], key: string): CountItem[] {
      const map = new Map<string, number>();
      for (const r of rows) { const v = r[key] as string | null; if (v) map.set(v, (map.get(v) ?? 0) + 1); }
      return Array.from(map.entries()).map(([label, count]) => ({ label, count })).sort((a, b) => b.count - a.count);
    }
    // 다중 선택(배열) 컬럼 집계
    function countArray(rows: Record<string, unknown>[], key: string): CountItem[] {
      const map = new Map<string, number>();
      for (const r of rows) { const arr = r[key] as string[] | null; if (arr) for (const v of arr) map.set(v, (map.get(v) ?? 0) + 1); }
      return Array.from(map.entries()).map(([label, count]) => ({ label, count })).sort((a, b) => b.count - a.count);
    }
    const dailyMap = new Map<string, number>();
    for (const r of surveyRows) {
      const d = new Date(r.applied_at as string).toLocaleDateString("ko-KR", { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit" });
      dailyMap.set(d, (dailyMap.get(d) ?? 0) + 1);
    }
    const daily = Array.from(dailyMap.entries()).map(([date, count]) => ({ date, count })).sort((a, b) => a.date.localeCompare(b.date));
    survey = {
      total: surveyRows.length, daily,
      format: countSingle(surveyRows, "survey_format"),
      days: countArray(surveyRows, "survey_days"),
      times: countArray(surveyRows, "survey_times"),
      region: countSingle(surveyRows, "survey_region"),
      status: countSingle(surveyRows, "survey_status"),
      channels: countArray(surveyRows, "survey_channels"),
      revenue: countSingle(surveyRows, "survey_revenue"),
      granter: countSingle(surveyRows, "survey_granter"),
      interests: countArray(surveyRows, "survey_interests"),
    };
  }

  return {
    users: regularUsers.length, admins: adminCount,
    applications: applications.count ?? 0, preorders: preorders.count ?? 0, payments: payments.count ?? 0,
    pending: pending.count ?? 0, paid: paid.count ?? 0, providers, survey,
  };
}

export default async function AdminDashboardPage({
  searchParams,
}: { searchParams: Promise<{ days?: string; from?: string; to?: string }> }) {
  const session = await auth();
  if (session?.user?.role !== "admin") redirect("/admin/signin");

  const { days, from, to } = await searchParams;
  const range = resolveRange({ days, from, to });
  const stats = await loadStats(range.startISO, range.endISO);

  return (
    <section className="admin-page">
      <div className="admin-page-head">
        <h1>대시보드</h1>
        <RangePicker basePath="/admin" range={range} />
      </div>
      {!stats ? (
        <p className="admin-warning">
          Supabase가 연결되지 않았습니다. <code>NEXT_PUBLIC_SUPABASE_URL</code>과 <code>SUPABASE_SERVICE_ROLE_KEY</code>를 설정하세요.
        </p>
      ) : (
        <>
          <div className="admin-stats">
            <Link href="/admin/users" className="stat stat-link">
              <p className="stat-k">가입자</p><p className="stat-v">{stats.users}</p>
              <p className="stat-sub">관리자 {stats.admins}명 별도</p>
            </Link>
            <Link href="/admin/applications" className="stat stat-link">
              <p className="stat-k">신청자</p><p className="stat-v">{stats.applications}</p>
              <p className="stat-sub">사전예약 {stats.preorders}명 · 정규교육 {stats.payments}명 · 미결제 {stats.pending}명</p>
            </Link>
            <div className="stat">
              <p className="stat-k">결제 완료</p><p className="stat-v sig">{stats.paid}</p>
              <p className="stat-sub">/ 얼리버드 {SEATS.earlybirdTotal}석</p>
            </div>
            <div className="stat">
              <p className="stat-k">결제 전환율</p>
              <p className="stat-v">{stats.applications > 0 ? `${Math.round((stats.paid / stats.applications) * 100)}%` : "—"}</p>
              <p className="stat-sub">결제완료 / 신청자</p>
            </div>
          </div>

          {stats.providers.length > 0 && (
            <div className="admin-card">
              <h2 className="admin-card-h">소셜 로그인 채널별 가입</h2>
              <ul className="admin-channel-list">
                {stats.providers.map((p) => (
                  <li key={p.provider}>
                    <span className={`provider provider-${p.provider}`}>{p.provider}</span>
                    <span className="admin-channel-bar-wrap">
                      <span className="admin-channel-bar" style={{ width: `${stats.users > 0 ? (p.count / stats.users) * 100 : 0}%` }} />
                    </span>
                    <span className="admin-channel-count">{p.count}명 ({stats.users > 0 ? Math.round((p.count / stats.users) * 100) : 0}%)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {stats.survey && stats.survey.total > 0 && <SurveyDashboard survey={stats.survey} />}

          <div className="admin-quick">
            <Link href="/admin/applications?status=pending" className="btn-secondary">미결제 신청자 보기 →</Link>
            <Link href="/admin/users" className="btn-secondary">전체 가입자 보기 →</Link>
          </div>
        </>
      )}
    </section>
  );
}
```

---

## 4. 차트 디자인 — `app/admin/SurveyDashboard.tsx` (Recharts)

설문 통계를 **Pie(단일선택) / 가로 Bar(다중선택) / Area(일별 추이)**로. 3-up 그리드(`admin-chart-grid`).
Pie는 도넛(innerRadius)+레전드, Bar는 vertical layout(긴 한글 라벨 대응), Area는 일별 추이(wide).

> 🎨 색: 여기 `COLORS`는 **범용 웹세이프 팔레트**. 트래픽(§5)은 **브랜드 토큰 팔레트**를 쓴다 → 브랜드 통일 권장.

```tsx
"use client";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area, CartesianGrid } from "recharts";

type CountItem = { label: string; count: number };
type DailyItem = { date: string; count: number };
export type SurveyStats = {
  total: number;
  format: CountItem[]; days: CountItem[]; times: CountItem[]; region: CountItem[]; status: CountItem[];
  channels: CountItem[]; revenue: CountItem[]; granter: CountItem[]; interests: CountItem[]; daily: DailyItem[];
};

const COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#e67e22", "#34495e"];
const LABELS: Record<string, string> = { online: "온라인", offline: "오프라인", both: "둘 다" };
function l(v: string) { return LABELS[v] ?? v; }

function PieSection({ title, items, total }: { title: string; items: CountItem[]; total: number }) {
  if (items.length === 0) return null;
  const data = items.map((i) => ({ name: l(i.label), value: i.count }));
  return (
    <div className="admin-chart-card">
      <h3 className="admin-chart-title">{title}</h3>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie data={data} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value"
            label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={true} style={{ fontSize: 11 }}>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip formatter={(v) => [`${v}명`, ""]} />
        </PieChart>
      </ResponsiveContainer>
      <ul className="admin-chart-legend">
        {items.map((item, i) => (
          <li key={item.label}>
            <span className="admin-chart-dot" style={{ background: COLORS[i % COLORS.length] }} />
            {l(item.label)} — {item.count}명 ({total > 0 ? Math.round((item.count / total) * 100) : 0}%)
          </li>
        ))}
      </ul>
    </div>
  );
}

function BarSection({ title, items }: { title: string; items: CountItem[] }) {
  if (items.length === 0) return null;
  const data = items.map((i) => ({ name: l(i.label), count: i.count }));
  return (
    <div className="admin-chart-card">
      <h3 className="admin-chart-title">{title}</h3>
      <ResponsiveContainer width="100%" height={Math.max(180, data.length * 36)}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
          <XAxis type="number" allowDecimals={false} />
          <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 12 }} />
          <Tooltip formatter={(v) => [`${v}명`, ""]} />
          <Bar dataKey="count" fill="#e74c3c" radius={[0, 4, 4, 0]} barSize={20} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function DailyChart({ daily }: { daily: DailyItem[] }) {
  if (daily.length === 0) return null;
  return (
    <div className="admin-chart-card admin-chart-wide">
      <h3 className="admin-chart-title">일별 사전예약 추이</h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={daily}>
          <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis allowDecimals={false} />
          <Tooltip formatter={(v) => [`${v}명`, ""]} />
          <Area type="monotone" dataKey="count" stroke="#e74c3c" fill="#e74c3c" fillOpacity={0.15} strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SurveyDashboard({ survey }: { survey: SurveyStats }) {
  return (
    <div className="admin-card">
      <h2 className="admin-card-h">사전예약 설문 통계 ({survey.total}명 응답)</h2>
      <DailyChart daily={survey.daily} />
      <div className="admin-chart-grid">
        <PieSection title="강의 형태" items={survey.format} total={survey.total} />
        <PieSection title="현재 상태" items={survey.status} total={survey.total} />
        <PieSection title="그랜터 사용" items={survey.granter} total={survey.total} />
      </div>
      <div className="admin-chart-grid">
        <BarSection title="선호 요일" items={survey.days} />
        <BarSection title="선호 시간대" items={survey.times} />
        <BarSection title="오프라인 지역" items={survey.region} />
      </div>
      <div className="admin-chart-grid">
        <BarSection title="판매 채널" items={survey.channels} />
        <BarSection title="월 매출 규모" items={survey.revenue} />
        <BarSection title="기대하는 강의 내용" items={survey.interests} />
      </div>
    </div>
  );
}
```

---

## 5. 트래픽 (GA4) — `lib/ga4.ts` + `traffic/page.tsx` + `TrafficCharts.tsx`

GA4 Data API(server-only). **refresh-token OAuth**로 access token 발급 → `runReport` 9개 병렬.
**모든 리포트에서 `/admin` 페이지뷰 제외**(운영자 방문이 통계를 오염시키던 문제 해결).
시크릿: `GA4_REFRESH_TOKEN` / `GA4_CLIENT_ID` / `GA4_CLIENT_SECRET` / `GA4_PROPERTY_ID` (Cloudflare secret / `.env.local`).

### `lib/ga4.ts`
```ts
import "server-only";

export type TrafficRow = { key: string; users: number; sessions: number };
export type HeatCell = { dow: number; hour: number; users: number }; // dow 0=일~6=토
export type TrafficData =
  | { configured: false }
  | {
      configured: true; activeDays: number; totalUsers: number; totalSessions: number;
      daily: TrafficRow[]; hourly: TrafficRow[]; heatmap: HeatCell[];
      channels: { label: string; sessions: number; users: number }[];
      devices: { label: string; users: number; sessions: number }[];
      newReturning: { label: string; users: number }[];
      events: { name: string; count: number }[];
      flow: { label: string; users: number }[];
    };

function env() {
  const refreshToken = process.env.GA4_REFRESH_TOKEN, clientId = process.env.GA4_CLIENT_ID,
    clientSecret = process.env.GA4_CLIENT_SECRET, propertyId = process.env.GA4_PROPERTY_ID;
  if (!refreshToken || !clientId || !clientSecret || !propertyId) return null;
  return { refreshToken, clientId, clientSecret, propertyId };
}

async function getAccessToken(e: NonNullable<ReturnType<typeof env>>): Promise<string> {
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ client_id: e.clientId, client_secret: e.clientSecret, refresh_token: e.refreshToken, grant_type: "refresh_token" }),
  });
  if (!res.ok) throw new Error(`GA4 token refresh failed: ${res.status}`);
  return ((await res.json()) as { access_token: string }).access_token;
}

type RunReportBody = { dateRanges: { startDate: string; endDate: string }[]; dimensions: { name: string }[]; metrics: { name: string }[]; orderBys?: unknown[] };

// 내부/어드민 트래픽 제외 — /admin 페이지뷰가 포함된 세션·이벤트를 모든 리포트에서 배제.
const EXCLUDE_ADMIN = { notExpression: { filter: { fieldName: "pagePath", stringFilter: { matchType: "BEGINS_WITH", value: "/admin" } } } };

async function runReport(e: NonNullable<ReturnType<typeof env>>, token: string, body: RunReportBody) {
  const res = await fetch(`https://analyticsdata.googleapis.com/v1beta/properties/${e.propertyId}:runReport`, {
    method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, dimensionFilter: EXCLUDE_ADMIN }),
  });
  if (!res.ok) throw new Error(`GA4 runReport failed: ${res.status}`);
  return res.json() as Promise<{ rows?: { dimensionValues: { value: string }[]; metricValues: { value: string }[] }[] }>;
}

export async function getTraffic(
  range: { startDate: string; endDate: string } = { startDate: "28daysAgo", endDate: "yesterday" },
): Promise<TrafficData> {
  const e = env();
  if (!e) return { configured: false };
  const token = await getAccessToken(e);

  const [totalsRes, dailyRes, hourlyRes, heatRes, chanRes, devRes, nvrRes, evtRes, pageRes] = await Promise.all([
    runReport(e, token, { dateRanges: [range], dimensions: [], metrics: [{ name: "activeUsers" }, { name: "sessions" }] }), // 기간전체 중복제거 1줄
    runReport(e, token, { dateRanges: [range], dimensions: [{ name: "date" }], metrics: [{ name: "activeUsers" }, { name: "sessions" }], orderBys: [{ dimension: { dimensionName: "date" } }] }),
    runReport(e, token, { dateRanges: [range], dimensions: [{ name: "hour" }], metrics: [{ name: "activeUsers" }, { name: "sessions" }], orderBys: [{ dimension: { dimensionName: "hour" } }] }),
    runReport(e, token, { dateRanges: [range], dimensions: [{ name: "dayOfWeek" }, { name: "hour" }], metrics: [{ name: "activeUsers" }] }),
    runReport(e, token, { dateRanges: [range], dimensions: [{ name: "sessionDefaultChannelGroup" }], metrics: [{ name: "sessions" }, { name: "activeUsers" }], orderBys: [{ metric: { metricName: "sessions" }, desc: true }] }),
    runReport(e, token, { dateRanges: [range], dimensions: [{ name: "deviceCategory" }], metrics: [{ name: "activeUsers" }, { name: "sessions" }], orderBys: [{ metric: { metricName: "activeUsers" }, desc: true }] }),
    runReport(e, token, { dateRanges: [range], dimensions: [{ name: "newVsReturning" }], metrics: [{ name: "activeUsers" }] }),
    runReport(e, token, { dateRanges: [range], dimensions: [{ name: "eventName" }], metrics: [{ name: "eventCount" }, { name: "activeUsers" }], orderBys: [{ metric: { metricName: "eventCount" }, desc: true }] }),
    runReport(e, token, { dateRanges: [range], dimensions: [{ name: "pagePath" }], metrics: [{ name: "screenPageViews" }, { name: "activeUsers" }], orderBys: [{ metric: { metricName: "screenPageViews" }, desc: true }] }),
  ]);

  const daily: TrafficRow[] = (dailyRes.rows ?? []).map((r) => ({ key: r.dimensionValues[0].value, users: Number(r.metricValues[0].value), sessions: Number(r.metricValues[1].value) }));
  const hourMap = new Map((hourlyRes.rows ?? []).map((r) => [r.dimensionValues[0].value, { users: Number(r.metricValues[0].value), sessions: Number(r.metricValues[1].value) }]));
  const hourly: TrafficRow[] = Array.from({ length: 24 }, (_, h) => { const k = String(h).padStart(2, "0"); const v = hourMap.get(k); return { key: k, users: v?.users ?? 0, sessions: v?.sessions ?? 0 }; });
  const heatmap: HeatCell[] = (heatRes.rows ?? []).map((r) => ({ dow: Number(r.dimensionValues[0].value), hour: Number(r.dimensionValues[1].value), users: Number(r.metricValues[0].value) }));
  const channels = (chanRes.rows ?? []).map((r) => ({ label: r.dimensionValues[0].value || "(기타)", sessions: Number(r.metricValues[0].value), users: Number(r.metricValues[1].value) }));
  const devices = (devRes.rows ?? []).map((r) => ({ label: r.dimensionValues[0].value, users: Number(r.metricValues[0].value), sessions: Number(r.metricValues[1].value) }));
  const newReturning = (nvrRes.rows ?? []).map((r) => ({ label: r.dimensionValues[0].value, users: Number(r.metricValues[0].value) })).filter((r) => r.label === "new" || r.label === "returning");
  const events = (evtRes.rows ?? []).map((r) => ({ name: r.dimensionValues[0].value, count: Number(r.metricValues[0].value) }));

  // 신청 플로우 퍼널 — 페이지/이벤트별 "활성 사용자" 근사치(엄밀한 순차 퍼널 아님).
  const evtUsers = new Map<string, number>((evtRes.rows ?? []).map((r) => [r.dimensionValues[0].value, Number(r.metricValues[1]?.value ?? 0)]));
  const pageUsers = new Map<string, number>((pageRes.rows ?? []).map((r) => [r.dimensionValues[0].value, Number(r.metricValues[1].value)]));
  const flow = [ // ⚠️ 경로/이벤트는 제품 라우트에 맞게 교체
    { label: "랜딩 방문", users: pageUsers.get("/") ?? 0 },
    { label: "회원가입 페이지 도달", users: pageUsers.get("/signup") ?? 0 },
    { label: "로그인 완료", users: evtUsers.get("login") ?? 0 },
    { label: "사전예약 페이지 도달", users: pageUsers.get("/preorder") ?? 0 },
    { label: "사전예약 완료(설문 제출)", users: pageUsers.get("/preorder/done") ?? 0 },
  ];

  const totalsRow = totalsRes.rows?.[0]; // 기간 전체 중복제거(일별 합산 아님)
  return {
    configured: true, activeDays: daily.length,
    totalUsers: Number(totalsRow?.metricValues[0]?.value ?? 0), totalSessions: Number(totalsRow?.metricValues[1]?.value ?? 0),
    daily, hourly, heatmap, channels, devices, newReturning, events, flow,
  };
}
```

### `traffic/page.tsx` (자체 기간선택 — GA4 상대날짜)
GA4는 `"28daysAgo"`/`"yesterday"`를 요구 → `adminRange` 대신 인라인 해석(프리셋 7/28/90, 기본 28). UI(`.range-*`)는 동일.

```tsx
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { getTraffic } from "@/lib/ga4";
import { TrafficCharts } from "./TrafficCharts";

export const dynamic = "force-dynamic";
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const PRESETS = [7, 28, 90] as const;

function parseYMD(s: string): Date { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
function addDays(b: Date, n: number): Date { const d = new Date(b); d.setDate(d.getDate() + n); return d; }
function fmtK(d: Date, withYear: boolean): string { const md = `${d.getMonth() + 1}월 ${d.getDate()}일`; return withYear ? `${d.getFullYear()}년 ${md}` : md; }

export default async function TrafficPage({ searchParams }: { searchParams: Promise<{ days?: string; from?: string; to?: string }> }) {
  const session = await auth();
  if (session?.user?.role !== "admin") redirect("/admin/signin");
  const { days, from, to } = await searchParams;

  const isCustom = !!from && !!to && DATE_RE.test(from) && DATE_RE.test(to) && from <= to;
  const preset = days === "7" ? 7 : days === "90" ? 90 : 28;
  const range = isCustom ? { startDate: from!, endDate: to! } : { startDate: `${preset}daysAgo`, endDate: "yesterday" };

  const now = new Date();
  const startD = isCustom ? parseYMD(from!) : addDays(now, -preset);
  const endD = isCustom ? parseYMD(to!) : addDays(now, -1);
  const topLabel = isCustom ? "맞춤 기간" : `지난 ${preset}일`;
  const rangeHuman = `${fmtK(startD, false)} ~ ${fmtK(endD, true)}`;

  let data: Awaited<ReturnType<typeof getTraffic>> | null = null, error: string | null = null;
  try { data = await getTraffic(range); } catch (e) { error = e instanceof Error ? e.message : "조회 실패"; }

  return (
    <section className="admin-section">
      <div className="admin-section-head">
        <h1>트래픽 (GA4)</h1>
        <details className="range-dd">
          <summary className="range-trigger">
            <span className="range-text"><span className="range-label">{topLabel}</span><span className="range-value">{rangeHuman}</span></span>
            <span className="range-caret" aria-hidden="true">▾</span>
          </summary>
          <div className="range-menu">
            <div className="range-presets">
              {PRESETS.map((n) => <Link key={n} href={`/admin/traffic?days=${n}`} className={!isCustom && preset === n ? "active" : ""}>지난 {n}일</Link>)}
            </div>
            <form method="get" className="range-form">
              <div className="range-fields">
                <input type="date" name="from" defaultValue={isCustom ? from : ""} aria-label="시작일" required />
                <span className="range-sep">~</span>
                <input type="date" name="to" defaultValue={isCustom ? to : ""} aria-label="종료일" required />
              </div>
              <button type="submit">조회</button>
            </form>
          </div>
        </details>
      </div>
      {error && <p className="legal-sub">GA4 조회 오류: {error}</p>}
      {data && !data.configured && <p className="legal-sub">GA4 자격증명 미설정 (Cloudflare 시크릿 GA4_REFRESH_TOKEN 등 필요)</p>}
      {data && data.configured && (
        <TrafficCharts periodLabel={rangeHuman} totalUsers={data.totalUsers} totalSessions={data.totalSessions} activeDays={data.activeDays}
          daily={data.daily} hourly={data.hourly} heatmap={data.heatmap} channels={data.channels} devices={data.devices}
          newReturning={data.newReturning} events={data.events} flow={data.flow} />
      )}
    </section>
  );
}
```

### `traffic/TrafficCharts.tsx` — 핵심: 커스텀 SVG 퍼널 + 히트맵
KPI 4개 + Pie 3개(채널/기기/신규vs재방문) + 일별 Area + 시간대 Bar + **퍼널 2개**(플로우·섹션) + **요일×시간 히트맵**.

**🎯 SVG 퍼널(`SectionFunnelCard`)** = 이 어드민의 시그니처. GA4 유입경로 탐색 스타일:
- 단계별 세로 막대가 기준(1단계=100%) 대비 높이로 taper.
- 상단 = 직전 대비 전환율 %, 하단 = 이탈률 `▼%`, **최대 이탈 구간 강조색**.
- **막대에 마우스 올릴 때만** 단계 연결 슬로프(polygon) 페이드인 — 상시 연결 아님(GA4 방식).
  (메모리 [[admin-funnel-design]]: 상시 연결형으로 바꾸지 말 것.)

```tsx
"use client";
import { useState } from "react";
import { ResponsiveContainer, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { LANDING_SECTIONS } from "@/lib/sections";

const SIGNAL = "#C84A1F"; // ⚠️ 브랜드 시그니처 색으로 교체
const COLORS = ["#C84A1F", "#E6883F", "#6C5CE7", "#3878DC", "#1FA37A", "#9aa0a6", "#D98AAE"];
const DOW = ["일", "월", "화", "수", "목", "금", "토"];
const CHAN_LABEL: Record<string, string> = { Direct: "직접", Referral: "추천(리퍼럴)", "Organic Search": "자연 검색", "Organic Social": "소셜", "Paid Search": "유료 검색", "Paid Social": "유료 소셜", Email: "이메일", Display: "디스플레이", Unassigned: "미할당" };
const DEVICE_LABEL: Record<string, string> = { desktop: "데스크탑", mobile: "모바일", tablet: "태블릿", "smart tv": "TV" };

type Row = { key: string; users: number; sessions: number };
type HeatCell = { dow: number; hour: number; users: number };
export type TrafficChartsProps = {
  periodLabel: string; totalUsers: number; totalSessions: number; activeDays: number;
  daily: Row[]; hourly: Row[]; heatmap: HeatCell[];
  channels: { label: string; sessions: number; users: number }[];
  devices: { label: string; users: number; sessions: number }[];
  newReturning: { label: string; users: number }[];
  events: { name: string; count: number }[];
  flow: { label: string; users: number }[];
};
const fmtDate = (d: string) => `${d.slice(4, 6)}/${d.slice(6, 8)}`;

function PieCard({ title, data, unit = "명" }: { title: string; data: { name: string; value: number }[]; unit?: string }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <div className="admin-chart-card">
      <h3 className="admin-chart-title">{title}</h3>
      {total === 0 ? <p className="admin-empty">데이터 없음</p> : (
        <>
          <ResponsiveContainer width="100%" height={190}>
            <PieChart>
              <Pie data={data} cx="50%" cy="50%" innerRadius={36} outerRadius={64} dataKey="value" stroke="none">
                {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v) => [`${v}${unit}`, ""]} />
            </PieChart>
          </ResponsiveContainer>
          <ul className="admin-chart-legend">
            {data.map((d, i) => <li key={d.name}><span className="admin-chart-dot" style={{ background: COLORS[i % COLORS.length] }} />{d.name} — {d.value} ({Math.round((d.value / total) * 100)}%)</li>)}
          </ul>
        </>
      )}
    </div>
  );
}

// GA4 유입경로(Funnel Exploration) 스타일 — 단계별 세로 영역 taper + 호버 시 단계 연결.
function SectionFunnelCard({ data, title = "섹션별 도달률 (이탈 지점)", note = "상단 % = 직전 단계 대비 전환율 · 하단 = 직전 대비 이탈률(▼) · 강조 = 최대 이탈 구간" }: { data: { name: string; value: number }[]; title?: string; note?: string }) {
  const [hover, setHover] = useState(false);
  const base = data[0]?.value ?? 0;
  const empty = data.every((d) => d.value === 0);
  const n = data.length;
  const H = 200, pad = 12, baseline = H - pad, usable = H - 2 * pad, colW = 100, W = Math.max(n * colW, 1);
  const yv = (v: number) => baseline - (base > 0 ? v / base : 0) * usable;
  const barL = (i: number) => i * colW + colW * 0.2;
  const barR = (i: number) => i * colW + colW * 0.8;
  let maxDropIdx = -1, maxDrop = -1;
  for (let i = 0; i < n - 1; i++) { const drop = data[i].value - data[i + 1].value; if (drop > maxDrop) { maxDrop = drop; maxDropIdx = i; } }
  const cols = `repeat(${n}, minmax(0, 1fr))`;

  return (
    <div className="admin-chart-card admin-chart-wide">
      <h3 className="admin-chart-title">{title}</h3>
      {empty ? <p className="admin-empty">데이터 없음</p> : (
        <div style={{ overflowX: "auto" }}>
          <div style={{ minWidth: n * 84, width: "100%" }}>
            {/* 헤더: 단계명 + 직전 대비 전환율 */}
            <div style={{ display: "grid", gridTemplateColumns: cols }}>
              {data.map((d, i) => {
                const conv = i === 0 ? 100 : data[i - 1].value > 0 ? Math.round((d.value / data[i - 1].value) * 100) : 0;
                return (
                  <div key={d.name} style={{ padding: "0 6px 6px", borderLeft: i ? "1px dashed rgba(0,0,0,.12)" : undefined }}>
                    <div style={{ fontSize: 11.5, fontWeight: 600, color: "#333", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{i + 1}. {d.name}</div>
                    <div style={{ fontSize: 12, color: "#888" }}>{d.value}명 · {conv}%</div>
                  </div>
                );
              })}
            </div>
            {/* 막대 + 호버 시 단계 연결(유입경로) 페이드인 */}
            <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none" style={{ display: "block" }}
              onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
              <g style={{ opacity: hover ? 1 : 0, transition: "opacity .35s ease" }}>
                {data.map((d, i) => i < n - 1 ? (
                  <polygon key={`c${i}`} points={`${barR(i)},${yv(d.value)} ${barL(i + 1)},${yv(data[i + 1].value)} ${barL(i + 1)},${baseline} ${barR(i)},${baseline}`}
                    fill={i === maxDropIdx && maxDrop > 0 ? "rgba(200,74,31,.3)" : "rgba(200,74,31,.16)"} />
                ) : null)}
              </g>
              {data.map((d, i) => <rect key={`b${i}`} x={barL(i)} y={yv(d.value)} width={barR(i) - barL(i)} height={baseline - yv(d.value)} fill={SIGNAL} fillOpacity={0.92} />)}
            </svg>
            {/* 하단: 이탈률 */}
            <div style={{ display: "grid", gridTemplateColumns: cols }}>
              {data.map((d, i) => {
                const drop = i < n - 1 ? d.value - data[i + 1].value : 0;
                const dropPct = i < n - 1 && d.value > 0 ? Math.round((drop / d.value) * 100) : 0;
                const isMax = i === maxDropIdx && maxDrop > 0;
                return (
                  <div key={d.name} style={{ padding: "5px 6px", borderLeft: i ? "1px dashed rgba(0,0,0,.12)" : undefined, fontSize: 11, color: "#999" }}>
                    {i < n - 1 && <>이탈 <b style={{ color: isMax ? SIGNAL : "#666" }}>▼{dropPct}%</b> <span style={{ color: "#bbb" }}>({drop})</span></>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
      <p className="traffic-axis meta">{note} · 막대에 마우스를 올리면 단계 연결이 표시됩니다</p>
    </div>
  );
}

export function TrafficCharts(p: TrafficChartsProps) {
  const dailyData = p.daily.map((r) => ({ label: fmtDate(r.key), 활성: r.users, 세션: r.sessions }));
  const hourlyData = p.hourly.map((r) => ({ label: `${Number(r.key)}`, 활성: r.users }));
  const peak = p.hourly.reduce((a, b) => (b.users > a.users ? b : a), p.hourly[0] ?? { key: "—", users: 0, sessions: 0 });
  const evtMap = new Map(p.events.map((e) => [e.name, e.count]));
  const sectionFunnelData = LANDING_SECTIONS.map((s) => ({ name: s.label, value: evtMap.get(s.event) ?? 0 }));
  const flowFunnelData = p.flow.map((f) => ({ name: f.label, value: f.users }));

  const heatLookup = new Map<string, number>();
  let heatMax = 0;
  for (const c of p.heatmap) { heatLookup.set(`${c.dow}-${c.hour}`, c.users); if (c.users > heatMax) heatMax = c.users; }
  const cellColor = (u: number) => u <= 0 ? "rgba(0,0,0,.04)" : `rgba(200,74,31,${(0.18 + 0.82 * (u / Math.max(heatMax, 1))).toFixed(3)})`;

  return (
    <div className="traffic-grid">
      <div className="traffic-summary">
        <div className="stat"><p className="stat-k">활성 사용자 ({p.periodLabel})</p><p className="stat-v">{p.totalUsers}</p></div>
        <div className="stat"><p className="stat-k">세션</p><p className="stat-v">{p.totalSessions}</p></div>
        <div className="stat"><p className="stat-k">일평균 사용자</p><p className="stat-v">{(p.daily.length ? p.daily.reduce((s, r) => s + r.users, 0) / p.daily.length : 0).toFixed(1)}</p></div>
        <div className="stat"><p className="stat-k">피크 시간대</p><p className="stat-v">{peak.users > 0 ? `${Number(peak.key)}시` : "—"}</p></div>
      </div>
      <div className="admin-chart-grid">
        <PieCard title="유입 채널" unit="세션" data={p.channels.map((c) => ({ name: CHAN_LABEL[c.label] ?? c.label, value: c.sessions }))} />
        <PieCard title="기기" data={p.devices.map((d) => ({ name: DEVICE_LABEL[d.label] ?? d.label, value: d.users }))} />
        <PieCard title="신규 vs 재방문" data={p.newReturning.map((n) => ({ name: n.label === "new" ? "신규" : "재방문", value: n.users }))} />
      </div>
      <div className="admin-chart-card admin-chart-wide">
        <h3 className="admin-chart-title">일별 추이</h3>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={dailyData} margin={{ left: -10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={16} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v, n) => [`${v}${n === "세션" ? "세션" : "명"}`, n as string]} />
            <Area type="monotone" dataKey="활성" stroke={SIGNAL} fill={SIGNAL} fillOpacity={0.14} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="admin-chart-card admin-chart-wide">
        <h3 className="admin-chart-title">시간대별 분포 (KST · 0~23시)</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={hourlyData} margin={{ left: -10, right: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eee" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={1} />
            <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v) => [`${v}명`, "활성 사용자"]} labelFormatter={(l) => `${l}시`} />
            <Bar dataKey="활성" fill={SIGNAL} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <SectionFunnelCard data={flowFunnelData} title="신청 플로우 퍼널 (랜딩→회원가입→로그인→사전예약→완료)"
        note="활성 사용자 기준 · 상단 % = 직전 단계 대비 전환율 · 하단 = 이탈률(▼) · 강조 = 최대 이탈 구간" />
      <SectionFunnelCard data={sectionFunnelData} />
      <div className="admin-chart-card admin-chart-wide">
        <h3 className="admin-chart-title">요일 × 시간 히트맵 (활성 사용자)</h3>
        <div className="heatmap" role="img" aria-label="요일별 시간대 트래픽 히트맵">
          <div className="heatmap-corner" />
          {Array.from({ length: 24 }, (_, h) => <div key={`hh${h}`} className="heatmap-hh">{h % 3 === 0 ? h : ""}</div>)}
          {DOW.map((d, dow) => <HeatRow key={d} day={d} dow={dow} get={(h) => heatLookup.get(`${dow}-${h}`) ?? 0} color={cellColor} />)}
        </div>
        <p className="traffic-axis meta">진할수록 활성 사용자 많음 · 가로=시각(0~23) · 세로=요일</p>
      </div>
    </div>
  );
}

function HeatRow({ day, dow, get, color }: { day: string; dow: number; get: (h: number) => number; color: (u: number) => string }) {
  return (
    <>
      <div className="heatmap-day">{day}</div>
      {Array.from({ length: 24 }, (_, h) => { const u = get(h); return <div key={`${dow}-${h}`} className="heatmap-cell" style={{ background: color(u) }} title={`${day} ${h}시 · ${u}명`} />; })}
    </>
  );
}
```

> 섹션 퍼널은 `LANDING_SECTIONS`(P8 `lib/sections.ts`)의 `{ label, event }`로 구동. GTM 섹션 도달 이벤트(`sec_01`~)와 1:1. 자세한 건 [[gtm-events.md]] / `tracking.md`.

---

## 6. 신청자 — `applications/page.tsx` + `SurveyDetail.tsx`

표 + 필터(검색 `q` · 유형 사전예약/정규 · 상태) + 기간(`RangePicker`) + CSV. ilike 검색은 `\%_` 이스케이프. 최근 500건.
각 행은 `SurveyDetail`(클라이언트)로 설문 펼침. 필터/기간을 export href에 그대로 전달.

```tsx
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import { resolveRange } from "@/lib/adminRange";
import { RangePicker } from "../RangePicker";
import { SurveyDetail } from "./SurveyDetail";

export const dynamic = "force-dynamic";

type Application = { id: string; user_id: string | null; name: string; email: string; phone: string; marketing_consent: boolean; cohort: string; status: string; is_preorder: boolean; applied_at: string; survey_format: string | null; survey_days: string[] | null; survey_times: string[] | null; survey_region: string | null; survey_status: string | null; survey_channels: string[] | null; survey_revenue: string | null; survey_granter: string | null; survey_interests: string[] | null; survey_comment: string | null; };
type SearchParams = Promise<{ q?: string; status?: string; type?: string; days?: string; from?: string; to?: string }>;

const STATUS_OPTIONS = [{ value: "", label: "전체 상태" }, { value: "pending", label: "대기 (미결제)" }, { value: "paid", label: "결제 완료" }, { value: "cancelled", label: "취소" }, { value: "refunded", label: "환불" }];
const TYPE_OPTIONS = [{ value: "", label: "전체 유형" }, { value: "preorder", label: "사전예약" }, { value: "payment", label: "정규교육" }];
function escapeIlike(q: string): string { return q.replace(/[\\%_]/g, (m) => `\\${m}`); }

async function loadApplications(q: string, status: string, type: string, startISO: string | null, endISO: string | null): Promise<Application[] | null> {
  const supabase = getSupabaseAdmin();
  if (!supabase) return null;
  let query = supabase.from("applications").select("*").order("applied_at", { ascending: false }).limit(500);
  if (startISO) query = query.gte("applied_at", startISO);
  if (endISO) query = query.lte("applied_at", endISO);
  if (q) { const safe = escapeIlike(q); query = query.or(`name.ilike.%${safe}%,email.ilike.%${safe}%,phone.ilike.%${safe}%`); }
  if (status) query = query.eq("status", status);
  if (type === "preorder") query = query.eq("is_preorder", true);
  else if (type === "payment") query = query.eq("is_preorder", false);
  const { data, error } = await query;
  if (error) { console.error("[admin.applications] load failed:", error); return []; }
  return data as Application[];
}

export default async function AdminApplicationsPage({ searchParams }: { searchParams: SearchParams }) {
  const session = await auth();
  if (session?.user?.role !== "admin") redirect("/admin/signin");
  const { q = "", status = "", type = "", days, from, to } = await searchParams;
  const range = resolveRange({ days, from, to });
  const apps = await loadApplications(q.trim(), status, type, range.startISO, range.endISO);

  const exportParams = new URLSearchParams();
  if (q) exportParams.set("q", q);
  if (status) exportParams.set("status", status);
  if (type) exportParams.set("type", type);
  if (range.isCustom) { exportParams.set("from", range.from!); exportParams.set("to", range.to!); }
  else if (range.preset !== "all") exportParams.set("days", range.preset);
  const qs = exportParams.toString();
  const exportHref = qs ? `/admin/applications/export.csv?${qs}` : "/admin/applications/export.csv";

  return (
    <section className="admin-page">
      <div className="admin-page-head">
        <div><h1>신청자</h1><p className="meta">최근 500건</p></div>
        <RangePicker basePath="/admin/applications" range={range} extra={{ q, status, type }} />
      </div>
      <form className="admin-toolbar" method="get" action="/admin/applications">
        <input type="search" name="q" defaultValue={q} placeholder="이름·이메일·연락처 검색" className="admin-search" />
        <select name="type" defaultValue={type} className="admin-select">{TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
        <select name="status" defaultValue={status} className="admin-select">{STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
        <button type="submit" className="btn-secondary">검색</button>
        {(q || status || type) && <a href="/admin/applications" className="btn-link-inline">초기화</a>}
        <span className="admin-toolbar-spacer" />
        <a href={exportHref} className="btn-secondary" download>CSV 내보내기</a>
      </form>
      {apps === null ? <p className="admin-warning">Supabase 미연결. 환경변수 설정 필요.</p>
        : apps.length === 0 ? <p className="admin-empty">{q || status || type || range.startISO ? "조건에 맞는 신청자가 없습니다." : "아직 신청자가 없습니다."}</p>
        : (
          <>
            <p className="meta admin-count">총 {apps.length}건</p>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead><tr><th>유형</th><th>이름</th><th>이메일</th><th>연락처</th><th>결제 상태</th><th>코호트</th><th>마케팅</th><th>설문</th><th>신청 시각</th></tr></thead>
                <tbody>{apps.map((a) => <SurveyDetail key={a.id} app={a} colCount={9} />)}</tbody>
              </table>
            </div>
          </>
        )}
    </section>
  );
}
```

`SurveyDetail.tsx` — 행 + 펼침(설문 상세 `<dl>`). 사전예약/정규 배지, 상태 배지, 설문 데이터 있을 때만 "보기" 버튼.

```tsx
"use client";
import { useState } from "react";

const FMT: Record<string, string> = { online: "온라인", offline: "오프라인", both: "둘 다" };
const STATUS_MAP: Record<string, string> = { pending: "대기", paid: "결제 완료", cancelled: "취소", refunded: "환불" };
type Application = { /* …위 page.tsx의 Application과 동일 부분집합… */ id: string; name: string; email: string; phone: string; is_preorder: boolean; status: string; cohort: string; marketing_consent: boolean; applied_at: string; survey_format: string | null; survey_days: string[] | null; survey_times: string[] | null; survey_region: string | null; survey_status: string | null; survey_channels: string[] | null; survey_revenue: string | null; survey_granter: string | null; survey_interests: string[] | null; survey_comment: string | null; };

export function SurveyDetail({ app: a, colCount }: { app: Application; colCount: number }) {
  const statusLabel = (s: string) => STATUS_MAP[s] ?? s;
  const [open, setOpen] = useState(false);
  const hasData = a.survey_format !== null;
  return (
    <>
      <tr>
        <td><span className={`status status-${a.is_preorder ? "preorder" : "payment"}`}>{a.is_preorder ? "사전예약" : "정규교육"}</span></td>
        <td>{a.name}</td><td>{a.email}</td><td>{a.phone}</td>
        <td><span className={`status status-${a.status}`}>{statusLabel(a.status)}</span></td>
        <td>{a.cohort}</td><td>{a.marketing_consent ? "동의" : "—"}</td>
        <td>{hasData ? <button type="button" className="survey-detail-btn" onClick={() => setOpen((v) => !v)}>{open ? "접기" : "보기"}</button> : <span className="admin-mute">—</span>}</td>
        <td>{new Date(a.applied_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}</td>
      </tr>
      {open && hasData && (
        <tr className="survey-detail-row">
          <td colSpan={colCount}>
            <dl className="survey-detail-list">
              <div><dt>강의형태</dt><dd>{FMT[a.survey_format!] ?? a.survey_format}</dd></div>
              <div><dt>요일</dt><dd>{a.survey_days?.join(", ") ?? "—"}</dd></div>
              <div><dt>시간대</dt><dd>{a.survey_times?.join(", ") ?? "—"}</dd></div>
              {a.survey_region && <div><dt>지역</dt><dd>{a.survey_region}</dd></div>}
              <div><dt>상태</dt><dd>{a.survey_status ?? "—"}</dd></div>
              <div><dt>채널</dt><dd>{a.survey_channels?.join(", ") ?? "—"}</dd></div>
              {a.survey_revenue && <div><dt>매출</dt><dd>{a.survey_revenue}</dd></div>}
              <div><dt>그랜터</dt><dd>{a.survey_granter ?? "—"}</dd></div>
              <div><dt>기대 내용</dt><dd>{a.survey_interests?.join(", ") ?? "—"}</dd></div>
              {a.survey_comment && <div><dt>의견</dt><dd>{a.survey_comment}</dd></div>}
            </dl>
          </td>
        </tr>
      )}
    </>
  );
}
```

---

## 7. 가입자 — `users/page.tsx`

신청자와 동형(표 + 검색 + 채널/권한 필터 + 기간 + CSV). **role 필터는 메모리에서**(`isAdminEmail`이 env 기반이라 DB push-down 불가).

```tsx
import { auth, isAdminEmail } from "@/lib/auth";
import { redirect } from "next/navigation";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import { resolveRange } from "@/lib/adminRange";
import { RangePicker } from "../RangePicker";

export const dynamic = "force-dynamic";

type User = { id: string; email: string; name: string | null; phone: string | null; provider: string | null; marketing_consent: boolean; created_at: string };
type SearchParams = Promise<{ q?: string; provider?: string; role?: string; days?: string; from?: string; to?: string }>;
const PROVIDER_OPTIONS = [{ value: "", label: "전체 채널" }, { value: "google", label: "Google" }, { value: "kakao", label: "Kakao" }, { value: "naver", label: "Naver" }];
const ROLE_OPTIONS = [{ value: "", label: "전체 권한" }, { value: "user", label: "일반 가입자" }, { value: "admin", label: "관리자" }];
function escapeIlike(q: string): string { return q.replace(/[\\%_]/g, (m) => `\\${m}`); }

async function loadUsers(q: string, provider: string, role: string, startISO: string | null, endISO: string | null): Promise<User[] | null> {
  const supabase = getSupabaseAdmin();
  if (!supabase) return null;
  let query = supabase.from("users").select("id, email, name, phone, provider, marketing_consent, created_at").order("created_at", { ascending: false }).limit(500);
  if (startISO) query = query.gte("created_at", startISO);
  if (endISO) query = query.lte("created_at", endISO);
  if (q) { const safe = escapeIlike(q); query = query.or(`name.ilike.%${safe}%,email.ilike.%${safe}%,phone.ilike.%${safe}%`); }
  if (provider) query = query.eq("provider", provider);
  const { data, error } = await query;
  if (error) { console.error("[admin.users] load failed:", error); return []; }
  let result = data as User[];
  if (role === "admin") result = result.filter((u) => isAdminEmail(u.email));
  else if (role === "user") result = result.filter((u) => !isAdminEmail(u.email));
  return result;
}

export default async function AdminUsersPage({ searchParams }: { searchParams: SearchParams }) {
  const session = await auth();
  if (session?.user?.role !== "admin") redirect("/admin/signin");
  const { q = "", provider = "", role = "", days, from, to } = await searchParams;
  const range = resolveRange({ days, from, to });
  const users = await loadUsers(q.trim(), provider, role, range.startISO, range.endISO);

  const exportParams = new URLSearchParams();
  if (q) exportParams.set("q", q);
  if (provider) exportParams.set("provider", provider);
  if (role) exportParams.set("role", role);
  if (range.isCustom) { exportParams.set("from", range.from!); exportParams.set("to", range.to!); }
  else if (range.preset !== "all") exportParams.set("days", range.preset);
  const qs = exportParams.toString();
  const exportHref = qs ? `/admin/users/export.csv?${qs}` : "/admin/users/export.csv";

  return (
    <section className="admin-page">
      <div className="admin-page-head">
        <div><h1>가입자</h1><p className="meta">소셜 로그인 기준 최근 500명</p></div>
        <RangePicker basePath="/admin/users" range={range} extra={{ q, provider, role }} />
      </div>
      <form className="admin-toolbar" method="get" action="/admin/users">
        <input type="search" name="q" defaultValue={q} placeholder="이름·이메일·연락처 검색" className="admin-search" />
        <select name="provider" defaultValue={provider} className="admin-select">{PROVIDER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
        <select name="role" defaultValue={role} className="admin-select">{ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
        <button type="submit" className="btn-secondary">검색</button>
        {(q || provider || role) && <a href="/admin/users" className="btn-link-inline">초기화</a>}
        <span className="admin-toolbar-spacer" />
        <a href={exportHref} className="btn-secondary" download>CSV 내보내기</a>
      </form>
      {users === null ? <p className="admin-warning">Supabase 미연결. 환경변수 설정 필요.</p>
        : users.length === 0 ? <p className="admin-empty">{q || provider || role || range.startISO ? "조건에 맞는 가입자가 없습니다." : "아직 가입자가 없습니다."}</p>
        : (
          <>
            <p className="meta admin-count">총 {users.length}명</p>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead><tr><th>권한</th><th>이름</th><th>이메일</th><th>연락처</th><th>로그인</th><th>마케팅</th><th>가입 시각</th></tr></thead>
                <tbody>
                  {users.map((u) => {
                    const admin = isAdminEmail(u.email);
                    return (
                      <tr key={u.id}>
                        <td><span className={admin ? "role-badge role-admin" : "role-badge role-user"}>{admin ? "관리자" : "일반"}</span></td>
                        <td>{u.name ?? "—"}</td><td>{u.email}</td><td>{u.phone ?? "—"}</td>
                        <td><span className={`provider provider-${u.provider}`}>{u.provider ?? "—"}</span></td>
                        <td>{u.marketing_consent ? "동의" : "—"}</td>
                        <td>{new Date(u.created_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
    </section>
  );
}
```

---

## 8. CSV Export — `*/export.csv/route.ts`

목록과 **동일한 필터/기간**을 받아 동일 결과를 CSV로. **BOM(`﻿`) + CRLF**(엑셀 한글), 셀 이스케이프, `no-store`, 401 가드.
limit만 10000으로 상향. 아래는 applications 버전(users도 동형).

```ts
import { auth } from "@/lib/auth";
import { getSupabaseAdmin } from "@/lib/supabase/server";
import { resolveRange } from "@/lib/adminRange";
import { type NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function escapeIlike(q: string): string { return q.replace(/[\\%_]/g, (m) => `\\${m}`); }
function csvCell(v: unknown): string {
  if (v === null || v === undefined) return "";
  const s = String(v);
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
function toCsvRow(cells: unknown[]): string { return cells.map(csvCell).join(","); }
const STATUS_LABEL: Record<string, string> = { pending: "대기", paid: "결제완료", cancelled: "취소", refunded: "환불" };

export async function GET(req: NextRequest) {
  const session = await auth();
  if (session?.user?.role !== "admin") return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const supabase = getSupabaseAdmin();
  if (!supabase) return NextResponse.json({ error: "supabase not configured" }, { status: 500 });

  const q = (req.nextUrl.searchParams.get("q") ?? "").trim();
  const status = (req.nextUrl.searchParams.get("status") ?? "").trim();
  const type = (req.nextUrl.searchParams.get("type") ?? "").trim();
  const range = resolveRange({ days: req.nextUrl.searchParams.get("days") ?? undefined, from: req.nextUrl.searchParams.get("from") ?? undefined, to: req.nextUrl.searchParams.get("to") ?? undefined });

  let query = supabase.from("applications").select("name, email, phone, status, cohort, marketing_consent, is_preorder, applied_at").order("applied_at", { ascending: false }).limit(10000);
  if (range.startISO) query = query.gte("applied_at", range.startISO);
  if (range.endISO) query = query.lte("applied_at", range.endISO);
  if (q) { const safe = escapeIlike(q); query = query.or(`name.ilike.%${safe}%,email.ilike.%${safe}%,phone.ilike.%${safe}%`); }
  if (status) query = query.eq("status", status);
  if (type === "preorder") query = query.eq("is_preorder", true);
  else if (type === "payment") query = query.eq("is_preorder", false);

  const { data, error } = await query;
  if (error) { console.error("[admin.applications.export] failed:", error); return NextResponse.json({ error: "query failed" }, { status: 500 }); }

  const headers = ["유형", "이름", "이메일", "연락처", "상태", "코호트", "마케팅동의", "신청시각"];
  const rows = (data ?? []).map((a) => [a.is_preorder ? "사전예약" : "정규교육", a.name, a.email, a.phone, STATUS_LABEL[a.status] ?? a.status, a.cohort, a.marketing_consent ? "Y" : "N", new Date(a.applied_at).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" })]);
  const csv = "﻿" + [toCsvRow(headers), ...rows.map(toCsvRow)].join("\r\n");
  const filename = `granter-applications-${new Date().toISOString().slice(0, 10)}.csv`;

  return new NextResponse(csv, { status: 200, headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="${filename}"`, "Cache-Control": "no-store" } });
}
```

---

## 9. CSS (globals.css에 복붙) — 어드민 전 영역

```css
/* ── ADMIN 네비/레이아웃 ── */
.admin-nav { background: var(--nav-dark); color: var(--nav-ink); border-bottom: 1px solid var(--ink); }
.admin-nav-inner { display: flex; align-items: center; justify-content: space-between; padding: .8rem 0; flex-wrap: wrap; gap: 1rem; }
.admin-logo { font-family: var(--font-display); font-weight: 700; letter-spacing: .04em; color: var(--nav-ink); text-decoration: none; }
.admin-tabs { display: flex; gap: 1.5rem; font-family: var(--font-body); font-size: 13px; letter-spacing: .06em; }
.admin-tabs a { color: var(--nav-ink); text-decoration: none; opacity: .7; }
.admin-tabs a:hover { opacity: 1; color: var(--signal); }
.admin-tabs .btn-link { color: var(--nav-ink); opacity: .7; text-decoration: underline; }
.admin-tabs .btn-link:hover { opacity: 1; color: var(--signal); }
.admin-main { padding: clamp(1.5rem, 4vw, 3rem) 0 5rem; min-height: calc(100vh - 60px); }
.admin-page, .admin-section { display: flex; flex-direction: column; gap: 1.5rem; }
.admin-section { gap: 1.4rem; }
.admin-page h1, .admin-section h1 { font-family: var(--font-display); font-weight: 600; font-size: clamp(1.6rem, 3vw, 2.2rem); }
.admin-page-head, .admin-section-head { display: flex; justify-content: space-between; align-items: end; flex-wrap: wrap; gap: 1rem; }
.admin-warning { background: #FFF7E6; border: 1px solid #F0B86E; padding: 1rem 1.2rem; font-size: .95rem; }
.admin-warning code { font-family: var(--font-body); background: rgba(0,0,0,.06); padding: .1rem .35rem; border-radius: 3px; }
.admin-empty { color: var(--mute); padding: 2rem 0; text-align: center; }

/* ── 통계 카드 ── */
.admin-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
.stat { background: #fff; border: 1px solid var(--rule); padding: 1.2rem 1.4rem; display: flex; flex-direction: column; gap: .4rem; }
.stat-k { font-family: var(--font-body); font-size: .75rem; letter-spacing: .12em; color: var(--mute); text-transform: uppercase; }
.stat-v { font-family: var(--font-display); font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 700; line-height: 1; }
.stat-v.sig { color: var(--signal); }
.stat-sub { font-size: .8rem; color: var(--mute); }
.stat-link { text-decoration: none; color: inherit; cursor: pointer; transition: border-color .15s ease, transform .15s ease; }
.stat-link:hover { border-color: var(--ink); transform: translateY(-2px); }
.admin-quick { display: flex; gap: .8rem; flex-wrap: wrap; }

/* ── 기간 선택 드롭다운(공용) ── */
.range-dd { position: relative; }
.range-dd > summary { list-style: none; cursor: pointer; }
.range-dd > summary::-webkit-details-marker { display: none; }
.range-trigger { display: flex; align-items: center; gap: .6rem; padding: .5rem .8rem; border: 1px solid var(--rule); background: #fff; min-width: 220px; }
.range-trigger:hover { border-color: #c9c9c2; }
.range-dd[open] .range-trigger { border-color: var(--ink); box-shadow: 0 2px 10px rgba(0,0,0,.06); }
.range-text { display: flex; flex-direction: column; line-height: 1.25; }
.range-label { font-size: .72rem; color: var(--mute); }
.range-value { font-size: .92rem; font-weight: 600; color: var(--ink); white-space: nowrap; }
.range-caret { margin-left: auto; color: var(--mute); font-size: .8rem; transition: transform .15s var(--ease); }
.range-dd[open] .range-caret { transform: rotate(180deg); }
.range-menu { position: absolute; right: 0; top: calc(100% + .4rem); z-index: 20; background: #fff; border: 1px solid var(--rule); box-shadow: 0 8px 28px rgba(0,0,0,.1); padding: .8rem; min-width: 280px; display: flex; flex-direction: column; gap: .7rem; }
.range-presets { display: flex; gap: .4rem; }
.range-presets a { flex: 1; text-align: center; padding: .4rem .2rem; border: 1px solid var(--rule); font-size: .82rem; color: var(--mute); text-decoration: none; }
.range-presets a:hover { border-color: var(--ink); color: var(--ink); }
.range-presets a.active { background: var(--ink); color: #fff; border-color: var(--ink); }
.range-form { display: flex; align-items: center; gap: .5rem; border-top: 1px solid var(--rule); padding-top: .7rem; }
.range-fields { display: flex; align-items: center; gap: .35rem; flex: 1; }
.range-fields input[type="date"] { flex: 1; min-width: 0; padding: .4rem .5rem; border: 1px solid var(--rule); font: inherit; font-size: .82rem; }
.range-sep { color: var(--mute); }
.range-form button { padding: .45rem .9rem; background: var(--ink); color: #fff; border: 0; font-size: .82rem; cursor: pointer; }
.range-form button:hover { opacity: .88; }
@media (max-width: 560px) { .range-menu { right: auto; left: 0; } }

/* ── 트래픽 ── */
.traffic-grid { display: flex; flex-direction: column; gap: 1.4rem; }
.traffic-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; }
.traffic-axis { margin-top: .5rem; }
.heatmap { display: grid; grid-template-columns: 2rem repeat(24, minmax(0, 1fr)); gap: 2px; }
.heatmap-hh { font-size: .62rem; color: var(--mute); text-align: center; font-variant-numeric: tabular-nums; }
.heatmap-day { font-size: .72rem; color: var(--mute); display: flex; align-items: center; }
.heatmap-cell { aspect-ratio: 1; border-radius: 3px; min-height: 14px; }

/* ── 표(신청자/가입자) ── */
.admin-table-wrap { overflow-x: auto; border: 1px solid var(--rule); background: #fff; }
.admin-table { width: 100%; border-collapse: collapse; font-size: .9rem; }
.admin-table th, .admin-table td { padding: .75rem 1rem; text-align: left; border-bottom: 1px solid var(--rule); white-space: nowrap; }
.admin-table th { font-family: var(--font-body); font-size: .75rem; letter-spacing: .1em; color: var(--mute); text-transform: uppercase; background: var(--paper); font-weight: 600; }
.admin-table tr:last-child td { border-bottom: 0; }
.status { font-family: var(--font-body); font-size: .72rem; letter-spacing: .08em; padding: .2rem .55rem; border: 1px solid var(--rule); }
.status-paid, .status-preorder { color: var(--signal); border-color: var(--signal); }
.status-pending { color: var(--mute); }
.status-cancelled, .status-refunded { color: var(--mute); text-decoration: line-through; }
.status-payment { color: var(--ink); border-color: var(--ink); }
.provider { color: var(--ink); }
.role-badge { font-family: var(--font-body); font-size: .72rem; letter-spacing: .06em; padding: .2rem .55rem; border: 1px solid var(--rule); white-space: nowrap; }
.role-admin { color: var(--signal); border-color: var(--signal); }
.role-user { color: var(--mute); }

/* ── 툴바(검색/CSV) ── */
.admin-toolbar { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; padding: .85rem; background: #fff; border: 1px solid var(--rule); }
.admin-toolbar-spacer { flex: 1; }
.admin-search { flex: 1; min-width: 200px; max-width: 360px; padding: .55rem .75rem; border: 1px solid var(--rule); background: #fff; font-size: .9rem; font-family: inherit; outline: none; }
.admin-search:focus { border-color: var(--ink); }
.admin-select { padding: .55rem .75rem; border: 1px solid var(--rule); background: #fff; font-size: .9rem; font-family: inherit; cursor: pointer; }
.btn-secondary { padding: .55rem 1rem; border: 1px solid var(--ink); background: #fff; color: var(--ink); font-size: .85rem; font-family: var(--font-body); letter-spacing: .04em; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: .3rem; }
.btn-secondary:hover { background: var(--ink); color: #fff; }
.btn-link-inline { color: var(--mute); font-size: .82rem; text-decoration: underline; padding: 0 .3rem; }
.btn-link-inline:hover { color: var(--ink); }
.admin-count { font-family: var(--font-body); font-size: .8rem; }

/* ── 대시보드 카드 / 채널 분포 / 차트 ── */
.admin-card { background: #fff; border: 1px solid var(--rule); padding: 1.2rem 1.4rem; }
.admin-card-h { font-family: var(--font-body); font-size: .78rem; letter-spacing: .12em; color: var(--mute); text-transform: uppercase; margin-bottom: 1rem; }
.admin-channel-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: .6rem; }
.admin-channel-list li { display: grid; grid-template-columns: 80px 1fr 120px; align-items: center; gap: .8rem; font-size: .9rem; }
.admin-channel-bar-wrap { display: block; height: 8px; background: var(--paper); border: 1px solid var(--rule); position: relative; overflow: hidden; }
.admin-channel-bar { display: block; height: 100%; background: var(--signal); transition: width .3s ease; }
.admin-channel-count { font-family: var(--font-body); font-size: .8rem; color: var(--mute); text-align: right; }
.admin-chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.2rem; margin-top: 1rem; }
.admin-chart-card { border: 1px solid var(--rule); border-radius: 8px; padding: 1rem; background: var(--bg); }
.admin-chart-wide { grid-column: 1 / -1; }
.admin-chart-title { font-size: .9rem; font-weight: 600; color: var(--ink); margin: 0 0 .5rem; }
.admin-chart-legend { list-style: none; padding: 0; margin: .5rem 0 0; display: flex; flex-wrap: wrap; gap: .4rem .8rem; font-size: .8rem; color: var(--mute); }
.admin-chart-legend li { display: flex; align-items: center; gap: .3rem; }
.admin-chart-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
.admin-mute { color: var(--mute); }

/* ── 신청자 설문 펼침 ── */
.survey-detail-btn { padding: .25rem .5rem; font-size: .78rem; border: 1px solid var(--rule); border-radius: 4px; background: var(--bg); color: var(--ink); cursor: pointer; white-space: nowrap; }
.survey-detail-btn:hover { border-color: var(--signal); }
.survey-detail-row td { padding: .5rem 1rem !important; background: var(--paper); }
.survey-detail-list { margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: .4rem 1.2rem; }
.survey-detail-list div { display: flex; gap: .4rem; font-size: .8rem; line-height: 1.4; }
.survey-detail-list dt { color: var(--mute); font-weight: 500; white-space: nowrap; }
.survey-detail-list dt::after { content: ":"; }
.survey-detail-list dd { color: var(--ink); margin: 0; }
```

> 토큰(`--ink`/`--rule`/`--mute`/`--paper`/`--signal`/`--nav-dark`/`--nav-ink`/`--bg`)은 P2 `design-system-skeleton.css` 것을 그대로 사용.

---

## 환불/취소 (원본 미구현 — 보강 권장)
`status`에 `cancelled`/`refunded` 값은 있으나 어드민 UI 액션 없음(수동/토스콘솔). 최소 **상태변경 + 토스 취소 API
(`/v1/payments/{key}/cancel`) 연동 + `applications.status` 동기화**. 환불정책(P0)과 일치시킬 것. ([[payment.md]] 웹훅과 함께.)

## 의존성·연계
- **P4 DB**: `users`·`applications`(설문 컬럼) → [[db-schema.sql]]. `getSupabaseAdmin()` → [[lib-core.md]].
- **P9 인증**: `auth()`·`signIn`·`isAdminEmail()`·role(jwt) → [[auth.md]]. `proxy.ts`가 `/admin` 미인증 리다이렉트.
- **P8 트래킹**: 섹션 퍼널은 `LANDING_SECTIONS`·GTM 섹션 이벤트 → [[tracking.md]] / [[gtm-events.md]].
- **트래픽 셋업**: GA4 OAuth refresh token 발급 → [[setup/gtm-ga4-setup.md]] · 시크릿은 [[env-vars.md]].
```
