export function Instructor() {
  return (
    <section className="section section-dark instructor" id="instructor" aria-labelledby="inst-h">
      <div className="wrap">
        <h2 id="inst-h" className="sr-only">
          강사 소개
        </h2>
        <div className="inst-hero">
          <div className="inst-portrait">
            <img src="/portrait-sample.png" alt="김민성 강사 (캐슬 AI)" />
          </div>
          <h3 className="inst-name">
            김민성 <span>강사</span>
          </h3>
          <p className="inst-lead">
            유튜브 1.4만 구독 &lsquo;캐슬 AI&rsquo;,{"\n"}
            현업 5년 차 엔지니어가 <span className="sig">직접</span> 가르칩니다
          </p>
          <ul className="inst-creds">
            <li>유튜브 &lsquo;캐슬 AI&rsquo; 1.4만 구독 채널 운영</li>
            <li>패스트캠퍼스 · 팀스파르타 · F-lab AI·바이브코딩 강사</li>
            <li>라포랩스(퀸잇) 서버 엔지니어 · MAU 300만 패션 커머스</li>
            <li>고용노동부 KDC(K-Digital Credit) 확인 강사</li>
            <li>위키북스 Claude Code 입문서 단독 집필 중</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
