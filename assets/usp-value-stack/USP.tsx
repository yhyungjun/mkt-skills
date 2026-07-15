// USP / 가치 총정리 섹션 — "이만큼 배우고 남긴다 · 남들엔 없는 N가지"
// 강의가 주는 차별적 가치(배우는 것·만드는 것·남는 것)를 번호 박스 그리드로
// 한 화면에 모아 각인시킨다. 해결(Solution) 직후 "왜 하필 이 강의냐"에 답하는 자리.
// 출처: granter-landing(USP) + axacademy-landing(ValueStack 각색).
// 외부 의존성 없음 — placeholder(중괄호)만 교체하면 그대로 동작.

const USPS = [
  { n: "첫 번째", title: "{차별점 1 제목}", desc: "{한 줄 설명 — 이 강의만 주는 결과·산출물}" },
  { n: "두 번째", title: "{차별점 2 제목}", desc: "{한 줄 설명}" },
  { n: "세 번째", title: "{차별점 3 제목}", desc: "{한 줄 설명}" },
  { n: "네 번째", title: "{차별점 4 제목}", desc: "{한 줄 설명}" },
  { n: "다섯 번째", title: "{차별점 5 제목}", desc: "{한 줄 설명}" },
  { n: "여섯 번째", title: "{차별점 6 제목}", desc: "{한 줄 설명}" },
] as const;

export function USP() {
  return (
    <section className="section section-dark usp" id="usp" aria-labelledby="usp-h">
      <div className="wrap">
        <div className="section-head reveal">
          <h2 id="usp-h">
            {"{기간}"} 동안, <span className="sig">이만큼</span> 배우고 남깁니다
          </h2>
          <p className="section-sub">다른 {"{카테고리}"} 강의엔 없는 {USPS.length}가지</p>
        </div>
        <div className="usp-grid reveal reveal-stagger">
          {USPS.map((u) => (
            <div key={u.n} className="usp-box">
              <span className="usp-n">{u.n}</span>
              <h3 className="usp-box-title">{u.title}</h3>
              <p className="usp-box-desc">{u.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
