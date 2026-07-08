# mkt-link

jocodingax.ai **UTM 링크 + Cloudflare 표시 링크**(`jocodingax.ai/go/{code}`)를 한 번에
생성·등록하는 스킬. 명령: `/mkt-link`.

## 무엇을 하나
유튜브/블로그 등 외부 게시물에 붙일 깔끔한 표시 링크를 만들고, 그게 UTM 붙은 실제 목적지로
301 리다이렉트되도록 Cloudflare Bulk Redirect에 자동 등록한다. UTM 컨벤션
(utm-youtube-convention)을 스크립트가 강제 검증하고, 슬러그 기반 mnemonic 숏코드를 자동 생성한다.

## 요건
- 실행 스크립트/토큰/레지스트리는 **marketing 레포**에 있다:
  - `~/Desktop/dev/marketing/ads/shortlink.py`
  - `~/Desktop/dev/marketing/ads/.cloudflare.env` (CF 토큰, gitignore)
  - `~/Desktop/dev/marketing/ads/shortlinks.json` (레지스트리, 커밋)

## 사용
"이 유튜브 커뮤니티 게시물 → 문의폼 표시링크 만들어줘" 처럼 **제목·종류·위치·목적지**만 주면
Claude가 `ads/shortlink.py add` 를 실행해 `jocodingax.ai/go/{code}` 를 반환하고 curl로 301을 검증한다.

전체 절차·값 매핑·예시는 `SKILL.md` 참고. 단순 UTM URL만 필요하면 `utm-tagging-jocodingax` 사용.
