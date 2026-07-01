"use client";

import { useEffect, useRef, useState } from "react";

export type ArtifactRow = { k: string; v?: string; sig?: boolean; sub?: boolean };

export type WeekDetail = {
  head: string;
  quote: string;
  bullets: { n: string; text: string }[];
  artifact: { label: string; rows: ArtifactRow[]; iframe?: string };
  banner: string;
  bannerVariant?: "default" | "climax";
};

export type Week = {
  badge: string;
  topic: string;
  summary: string;
  time: string;
  variant?: "free" | "climax";
  detail?: WeekDetail;
};

export const WEEKS: Week[] = [
  {
    badge: "FREE",
    topic: "Claude Code + 그랜터 시작",
    summary: "-Claude Code\n설치·기초 활용\n-그랜터 가입·온보딩 + MCP 연결 → 매출 데이터 조회",
    time: "60 MIN",
    variant: "free",
  },
  {
    badge: "W1",
    topic: "스킬 만들기",
    summary: "제공 스킬 3개(법적 검토·리뷰 답글·경쟁사 분석) + 본인 자작 스킬 1개",
    time: "90 MIN",
    detail: {
      head: "스킬 3개는 바로 쓰고, 1개는 직접 만든다.",
      quote: "법적 검토·리뷰 응대·경쟁사 분석, 매번 하던 일이 한 마디로 끝난다.",
      bullets: [
        { n: "01", text: "법적 리스크 검토 스킬 — 상세페이지·광고 카피의 식약처·표시광고법 위반 자동 검토." },
        { n: "02", text: "리뷰 답글 초안 스킬 — 별점·키워드 분류 + 부정 리뷰 필터 + 답글 자동 생성." },
        { n: "03", text: "경쟁사 상품 분석 스킬 — 포지셔닝·강조점·리뷰 분석으로 내 상품 차별화 갭 정리." },
        { n: "04", text: "본인 자작 스킬 워크숍 — Claude Skill Creator로 본인 반복 업무를 스킬로 직접 제작." },
      ],
      artifact: {
        label: "스킬 예시 — 수업에서 만드는 자동화 스킬",
        iframe: "/examples/skill-demo.html",
        rows: [
          { k: "$ legal-check", v: "위험 표현 2건 감지", sig: true },
          { k: "ISSUE 01 · 식약처 미인증 효능", sub: true },
          { k: '"면역력 강화"는 일반 식품 표시 불가 (식약처 가이드라인 위반)' },
          { k: "ISSUE 02 · 단정 표현", sub: true },
          { k: '"7일 만에 컨디션 개선" 효과 단정 — 표시광고법 위반 가능성' },
          { k: "→ 수정 제안", sub: true },
          { k: '"건강한 일상에 활력을 더하는 데일리 콜라겐"' },
        ],
      },
      banner: "매주 본인 그랜터를 동일 구조로 세팅합니다. W4 졸업 시 본인 워크스페이스로 그대로 옮겨집니다.",
    },
  },
  {
    badge: "W2",
    topic: "OS 데이터 레이어",
    summary: "-본인 채널 API 직접 연동\n-상품별 순이익·매출·재고 데이터 확보",
    time: "90 MIN",
    detail: {
      head: "본인 채널 데이터를 직접 연결한다. OS의 토대.",
      quote: "그랜터를 쓰는 이유가 바로 이거다 — 매출 데이터가 한 곳에 모인다.",
      bullets: [
        { n: "01", text: "API 개념 이해 & 데이터 구조 — 그랜터 MCP + 채널 API의 JSON 구조 파악." },
        { n: "02", text: "채널 데이터 연동 — 쿠팡·스마트스토어 상품별 매출·재고 데이터 수집." },
        { n: "03", text: "매출·재고 데이터 조회 — 상품별 순이익(매출 − 원가 − 수수료 − 광고비), 채널별 비중, 재고 소진 임박 조회." },
      ],
      artifact: {
        label: "OS 데이터 레이어 — 채널 연동 결과",
        iframe: "/examples/os-data-layer.html",
        rows: [
          { k: "월 매출", v: "₩ 287.4M", sig: true },
          { k: "▲ 18.4% vs. 전월" },
          { k: "활성 채널", v: "5" },
          { k: "재고 위험", v: "3", sig: true },
        ],
      },
      banner: "본인 그랜터를 동일 구조로 세팅하세요. W4 졸업 시 본인 매출·재고 데이터로 OS가 그대로 옮겨갑니다.",
    },
  },
  {
    badge: "W3",
    topic: "셀러 OS 기본 구축",
    summary: "-본인 HTML 대시보드 시각화\n-클로드 API 연동\n-셀러 OS 개발",
    time: "90 MIN",
    detail: {
      head: "데이터가 한 화면에. 본인만의 셀러 OS를 만든다.",
      quote: "조회·계산한 데이터를 한 화면에 — 어떤 상품이 진짜 돈이 되는지가 보인다.",
      bullets: [
        { n: "01", text: "본인만의 HTML 대시보드 시각화 (OS V1) — 순이익·매출·재고를 한 화면에서 추적." },
        { n: "02", text: "OS 큰그림 그리기 — 최종 OS 개요 스케치. 데이터 소스 → 판단 → 출력이 어떻게 연결되는지." },
        { n: "03", text: "클로드 API 키 발급 & 연동 — OS가 코드로 클로드를 호출하는 연동." },
        { n: "04", text: "셀러 OS 개발 — 그랜터 API + 재고 데이터를 클로드 API에 분석 요청 → 결과 수신을 한 스크립트로 연결." },
      ],
      artifact: {
        label: "셀러 OS 예시 — 수업에서 직접 만드는 화면",
        iframe: "/examples/os-seller.html",
        rows: [
          { k: "순이익", v: "₩ 1,496만", sig: true },
          { k: "매출", v: "₩ 3,050만" },
          { k: "재고 위험 SKU", v: "4개", sig: true },
        ],
      },
      banner: "본인 그랜터에 동일 구조로 세팅하세요. W4 졸업에서 본인 데이터로 OS가 그대로 작동합니다.",
    },
  },
  {
    badge: "W4",
    topic: "졸업 · 운영 시작",
    summary: "-AI 위험 알림 (슬랙/이메일)\n-본인 데이터 마이그레이션\n-클로드 코드 심화",
    time: "120 MIN",
    variant: "climax",
    detail: {
      head: '"이거, 진짜 내 사업이다" — 알림이 오고, 도구가 작동하고, 매일 쓴다.',
      quote: "자금 부족도, 품절도, 사업이 알아서 알려준다. 강의 자료가 아닌 운영 자산.",
      bullets: [
        { n: "01", text: "AI 위험 분석 & 알림 연동 — 클로드 API에 분석 프롬프트 작성, 임계 돌파 시 슬랙/이메일 자동 발송." },
        { n: "02", text: "본인 워크스페이스 점검 & 마이그레이션 마무리 — 공용→본인 데이터 전환 확인, 미완료자 보조강사 지원." },
        { n: "03", text: "니즈별 개인 커스터마이징 — 대시보드 지표·임계치·추적 채널을 본인 회사 기준으로. W1 자작 스킬 통합." },
        { n: "04", text: "클로드 코드 심화 — 커뮤니티 스킬 활용. 강의 후에도 스스로 도구를 늘릴 수 있게." },
      ],
      artifact: {
        label: "졸업 후 — 본인 워크스페이스",
        iframe: "/examples/os-mygranter.html",
        rows: [
          { k: "★ 본인 워크스페이스 · ACTIVE", sig: true },
          { k: "월 매출", v: "₩ 287M" },
          { k: "가용 자금", v: "₩ 142M" },
          { k: "재고 위험", v: "3종" },
          { k: "AI 알림", v: "2건", sig: true },
        ],
      },
      banner: "지난 4주간 본인 그랜터에 쌓아온 데이터가 OS로 그대로 옮겨집니다.\n졸업은 시험이 아니라, 매일 쓰는 도구의 활성화입니다.",
      bannerVariant: "climax",
    },
  },
];

export function Curriculum() {
  const chapters = WEEKS.filter((w): w is Week & { detail: WeekDetail } => Boolean(w.detail));
  const n = chapters.length;

  const trackRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const activeRef = useRef(0);
  const [railVisible, setRailVisible] = useState(false);
  const railRef = useRef(false);
  const lockRef = useRef(false);

  // scroll position (page Y) that centers week `i` (weeks map 1:1 onto the pinned scroll)
  const scrollToIndex = (i: number) => {
    const track = trackRef.current;
    if (!track) return;
    if (!track.classList.contains("curri-scrub")) {
      track.querySelector<HTMLElement>(`#chapter-${chapters[i]?.badge}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    const rect = track.getBoundingClientRect();
    const span = rect.height - window.innerHeight;
    const denom = Math.max(1, n - 1);
    const target = window.scrollY + rect.top + span * (i / denom);
    window.scrollTo({ top: target, behavior: "smooth" });
  };

  const scrollToBadge = (badge: string) => {
    const i = chapters.findIndex((c) => c.badge === badge);
    if (i >= 0) scrollToIndex(i);
  };

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;

    const headPanels = Array.from(track.querySelectorAll<HTMLElement>(".cs-panel-head"));
    const bodyPanels = Array.from(track.querySelectorAll<HTMLElement>(".cs-panel-body"));
    const visualPanels = Array.from(track.querySelectorAll<HTMLElement>(".cs-panel-visual"));
    const allPanels = [...headPanels, ...bodyPanels, ...visualPanels];

    const mqReduce = window.matchMedia("(prefers-reduced-motion: reduce)");
    const mqSmall = window.matchMedia("(max-width: 768px)");
    const enabled = () => !mqReduce.matches && !mqSmall.matches;

    let raf = 0;
    let scheduled = false;

    // Each week OWNS most of its scroll segment: a long fully-visible HOLD where the
    // macbook + copy sit still and readable, with a short overlapping CROSSFADE only at
    // the boundary between weeks (no blank handoff). Macbook + copy enter together.
    const PLT = 0.34; // half-width of the fully-visible hold (op = 1)
    const FADE = 0.3; // crossfade band; PLT+FADE > 0.5 so neighbours overlap (no blank)
    const opacityFor = (d: number) => Math.min(1, Math.max(0, (PLT + FADE - d) / FADE));
    // motion ramp: 1 (settled/still) across the hold, eases to 0 only in the transition
    const motionFor = (d: number) => {
      const m = Math.min(1, Math.max(0, (0.5 - d) / (0.5 - PLT)));
      return m * m * (3 - 2 * m); // smoothstep
    };

    // VISUAL (live demo frame) — subtle 2D settle (slide + scale) during the boundary
    // transition only; dead-still and full-size across the hold so the iframe is legible.
    const paintVisual = (panels: HTMLElement[], t: number) => {
      panels.forEach((el, i) => {
        const d = Math.abs(t - i);
        const op = opacityFor(d);
        const m = motionFor(d);
        const dir = i - t; // >0 entering (from below), <0 leaving (upward)
        const ty = dir * 24 * (1 - m);
        const scale = 0.96 + m * 0.04;
        el.style.opacity = op.toFixed(3);
        el.style.transform = `translateY(${ty.toFixed(1)}px) scale(${scale.toFixed(3)})`;
        const front = op > 0.5;
        el.style.zIndex = front ? "2" : "1";
        el.style.pointerEvents = front ? "auto" : "none";
      });
    };

    // TEXT — same hold/crossfade window as the visual (they enter together). The copy
    // assembles FAST on entry (--ip 0→1 over ~0.22 segment) then holds fully visible.
    const paintText = (panels: HTMLElement[], t: number) => {
      panels.forEach((el, i) => {
        const d = Math.abs(t - i);
        const op = opacityFor(d);
        const ip = Math.min(1, Math.max(0, (t - (i - 0.5)) / 0.22));
        const m = motionFor(d);
        const dir = i - t;
        el.style.opacity = op.toFixed(3);
        el.style.setProperty("--ip", ip.toFixed(3));
        el.style.transform = `translateY(${(dir * 10 * (1 - m)).toFixed(1)}px)`;
        const front = op > 0.5;
        el.style.zIndex = front ? "2" : "1";
        el.style.pointerEvents = front ? "auto" : "none";
      });
    };

    const update = () => {
      scheduled = false;
      const on = enabled();
      track.classList.toggle("curri-scrub", on);

      if (!on) {
        allPanels.forEach((el) => {
          el.style.opacity = "";
          el.style.transform = "";
          el.style.zIndex = "";
          el.style.pointerEvents = "";
          el.style.removeProperty("--ip");
          el.style.removeProperty("--open");
        });
        track.style.removeProperty("--P");
        if (railRef.current) {
          railRef.current = false;
          setRailVisible(false);
        }
        return;
      }

      const vh = window.innerHeight;
      const rect = track.getBoundingClientRect();

      // rail only while the pinned scene occupies the viewport center
      const inView = rect.top < vh * 0.5 && rect.bottom > vh * 0.5;
      if (inView !== railRef.current) {
        railRef.current = inView;
        setRailVisible(inView);
      }

      const span = rect.height - vh;
      const P = span > 0 ? Math.min(1, Math.max(0, -rect.top / span)) : rect.top <= 0 ? 1 : 0;
      // weeks map 1:1 onto the pinned scroll: W1 full at pin, last week full at the end
      const t = P * Math.max(1, n - 1);

      track.style.setProperty("--P", P.toFixed(4));
      paintVisual(visualPanels, t);
      paintText(headPanels, t);
      paintText(bodyPanels, t);

      const idx = Math.min(n - 1, Math.max(0, Math.round(t)));
      if (idx !== activeRef.current) {
        activeRef.current = idx;
        setActiveIndex(idx);
      }
    };

    const onScroll = () => {
      if (scheduled) return;
      scheduled = true;
      raf = requestAnimationFrame(update);
    };

    // ── snap stepping: one scroll GESTURE = exactly one week, no matter how soft or hard
    // the swipe is. a trackpad fling (and fast wheel bursts) emit a long stream of events;
    // we step on the FIRST, swallow the rest, and only re-arm once the stream goes idle.
    const IDLE_MS = 180; // gap that marks the end of a wheel/momentum stream
    let idleTimer = 0;
    const armRelease = () => {
      window.clearTimeout(idleTimer);
      idleTimer = window.setTimeout(() => { lockRef.current = false; }, IDLE_MS);
    };
    const isPinned = () => {
      const vh = window.innerHeight;
      const rect = track.getBoundingClientRect();
      return rect.top <= 1 && rect.bottom >= vh - 1;
    };
    const curIndex = () => {
      const rect = track.getBoundingClientRect();
      const span = rect.height - window.innerHeight;
      const P = span > 0 ? Math.min(1, Math.max(0, -rect.top / span)) : 0;
      return Math.round(P * Math.max(1, n - 1));
    };
    const tryStep = (dir: number) => {
      // mid-gesture (momentum still flowing): swallow everything, push the re-arm later
      if (lockRef.current) { armRelease(); return true; }
      const next = curIndex() + dir;
      if (next < 0 || next > n - 1) return false; // fresh gesture at an end → release native
      lockRef.current = true;
      scrollToIndex(next);
      armRelease();
      return true;
    };
    const onWheel = (e: WheelEvent) => {
      if (!track.classList.contains("curri-scrub") || !isPinned()) return;
      const dir = e.deltaY > 0 ? 1 : e.deltaY < 0 ? -1 : 0;
      if (dir && tryStep(dir)) e.preventDefault();
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (!track.classList.contains("curri-scrub") || !isPinned()) return;
      const down = e.key === "ArrowDown" || e.key === "PageDown" || (e.key === " " && !e.shiftKey);
      const up = e.key === "ArrowUp" || e.key === "PageUp" || (e.key === " " && e.shiftKey);
      const dir = down ? 1 : up ? -1 : 0;
      if (dir && tryStep(dir)) e.preventDefault();
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    window.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("keydown", onKeyDown);
    return () => {
      cancelAnimationFrame(raf);
      window.clearTimeout(idleTimer);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      window.removeEventListener("wheel", onWheel);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [n]);

  return (
    <section className="section curriculum" id="curriculum" aria-labelledby="curri-h">
      <div className="wrap">
        <div className="section-head">
          <h2 id="curri-h">
            5단계로 자기 사업의 <span className="sig">OS</span>를 완성한다
          </h2>
        </div>

        <ul className="curri-grid">
          {WEEKS.map((w) => (
            <li
              key={w.badge}
              className={`curri-card${w.variant ? ` ${w.variant}` : ""}${w.detail ? " clickable" : ""}`}
              onClick={w.detail ? () => scrollToBadge(w.badge) : undefined}
              role={w.detail ? "button" : undefined}
              tabIndex={w.detail ? 0 : undefined}
              onKeyDown={w.detail ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); scrollToBadge(w.badge); } } : undefined}
            >
              <p className="cc-week">{w.badge}</p>
              <h3 className="cc-topic">{w.topic}</h3>
              <p className="cc-sum">
                {w.summary.split("\n").map((line, i) => (
                  <span key={i} className="cc-sum-line">
                    {line}
                  </span>
                ))}
              </p>
              <p className="cc-time">{w.time}</p>
            </li>
          ))}
        </ul>

        <nav className={`curri-rail${railVisible ? " visible" : ""}`} aria-label="커리큘럼 단계 이동">
          {chapters.map((w, i) => (
            <button
              key={w.badge}
              type="button"
              className={`curri-rail-dot${activeIndex === i ? " active" : ""}`}
              onClick={() => scrollToIndex(i)}
              aria-current={activeIndex === i ? "true" : undefined}
            >
              <span className="curri-rail-label">{w.badge}</span>
            </button>
          ))}
        </nav>

        {/* single pinned scene: one sticky stage, weeks crossfade as you scroll */}
        <div className="curri-track" ref={trackRef} style={{ ["--n" as string]: n }}>
          <div className="curri-scene">
            <div className="cs-grid">
              {/* TOP: week badge + headline */}
              <div className="cs-head-stack">
                {chapters.map((w) => {
                  const d = w.detail;
                  const isClimax = w.variant === "climax";
                  return (
                    <article
                      key={w.badge}
                      id={`chapter-${w.badge}`}
                      className={`cs-panel cs-panel-head${isClimax ? " climax" : ""}`}
                      aria-labelledby={`cd-${w.badge}-h`}
                    >
                      <p className="cd-week">
                        {w.badge} <span className="cd-meta">· {w.time} · {w.topic}</span>
                      </p>
                      <h3 id={`cd-${w.badge}-h`} className="cd-head cs-head">
                        {d.head}
                      </h3>
                    </article>
                  );
                })}
              </div>

              {/* MIDDLE: live demo */}
              <aside className="cs-visual-stack" aria-hidden="true">
                {chapters.map((w) => {
                  const d = w.detail;
                  return (
                    <div key={w.badge} className="cs-panel cs-panel-visual">
                      {d.artifact.iframe ? (
                        <figure className="laptop">
                          <div className="laptop-screen">
                            <span className="laptop-notch" aria-hidden="true" />
                            <div className="laptop-viewport">
                              <iframe
                                src={d.artifact.iframe}
                                className="laptop-iframe"
                                title={d.artifact.label}
                                loading="lazy"
                                scrolling="yes"
                              />
                            </div>
                          </div>
                          <div className="laptop-base" aria-hidden="true" />
                          <figcaption className="laptop-caption">{d.artifact.label}</figcaption>
                        </figure>
                      ) : (
                        <div className="artifact cd-artifact" data-label={d.artifact.label}>
                          {d.artifact.rows.map((r, i) =>
                            r.sub ? (
                              <div key={i} className="artifact-sub">
                                {r.k}
                              </div>
                            ) : (
                              <div key={i} className="row">
                                <span className="k">{r.k}</span>
                                {r.v ? <span className={`v${r.sig ? " sig" : ""}`}>{r.v}</span> : null}
                              </div>
                            )
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </aside>

              {/* BOTTOM: quote + bullets + banner */}
              <div className="cs-body-stack">
                {chapters.map((w) => {
                  const d = w.detail;
                  return (
                    <div key={w.badge} className="cs-panel cs-panel-body">
                      <p className="cd-quote cs-quote">{d.quote}</p>
                      <ul className="cs-bullets" role="list">
                        {d.bullets.map((b, bi) => (
                          <li key={b.n} className="cs-bullet" style={{ ["--bi" as string]: bi }}>
                            <span className="cd-n">{b.n}</span>
                            <span>{b.text}</span>
                          </li>
                        ))}
                      </ul>
                      <p className={`cd-banner cs-banner${d.bannerVariant === "climax" ? " climax" : ""}`}>
                        <span className="cd-banner-pip" aria-hidden="true">
                          {d.bannerVariant === "climax" ? "★" : "!"}
                        </span>
                        {d.banner}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
