---
name: mkt-blog-writing
description: |
  SEO 최적화 블로그 글을 7단계로 작성·발행하는 마케팅 블로그 스킬. 유형 선택(정보제공/자사홍보/포트폴리오/일상)
  → Limbic 독자분석 → 키워드 → 제목 → 도입부 → 본문 → CTA → (썸네일) → 발행까지 순차 진행한다.
  각 단계는 reference/ 문서를 참조하며, bonda MCP(키워드·발행·추적링크)와 inblog CLI(초안·CTA·커버) 연동.
  Use when asked to "블로그 써줘", "SEO 블로그 작성", "블로그 글 만들어", "마케팅 블로그 글",
  "포트폴리오/도입사례 블로그", "/mkt-blog-writing". (조코딩AX 인블로그·네이버 발행 기본값 내장.)
---


# Bonda Skill — 7단계 블로그 생성 워크플로우

이 Skill은 `/mkt-blog-writing` 입력 시 SEO 최적화 블로그 글을 7단계로 작성한다.
reference/ 문서를 각 단계에서 반드시 참조한다.

---

## 실행 규칙

1. `/mkt-blog-writing` 또는 "블로그 작성" 언급 시 즉시 Step 1을 시작한다.
2. 각 단계는 이전 단계 완료 후에 진행한다.
3. 사용자가 단계를 건너뛰길 원하면 허용하되, 필수 입력이 없으면 기본값 또는 추론값을 명시한다.
4. `reference/` 문서를 각 단계에서 참조한다 (아래 "단계별 참조 파일" 섹션 확인).
5. DAILY 유형은 Limbic 분석과 Step 2(키워드)를 생략한다 (limbic_type = None).
6. 제목이 마음에 들지 않으면 동일한 keyword와 limbic_type을 유지한 채 최대 3회 재생성한다.
7. 강점(strengths) 미입력 시 건너뛰기 허용, 도입부/본문에서 강점 항목 생략.

---

## 내부 상태 (blog_context)

Step 진행 중 아래 값을 누적 유지한다.

```
blog_context = {
  "blog_type": "INFO" | "PURCHASE" | "PORTFOLIO" | "DAILY",
  "company_name": str | None,
  "company_service": str | None,
  "strengths": [
    {
      "title": str,
      "description": str,
      "image_urls": list[str],       # 강점당 최대 4장 (CLAUDE.md 도메인 룰)
      "image_layout": str | None,
      "is_active": bool,
    }
  ] | None,
  "limbic_type": "traditionalist" | "performer" | "hedonist" | "disciplinarian" | None,
  "dominant_emotion": str | None,
  "user_provided_info": str | None,        # INFO
  "target_audience": str | None,           # PURCHASE
  "target_problem": str | None,            # PURCHASE
  "target_desired_outcome": str | None,    # PURCHASE — 내 서비스를 실제로 써본 뒤 타겟의 변화 (글을 읽은 직후 결심 X)
  "customer_problem": str | None,          # PORTFOLIO
  "solution": str | None,                  # PORTFOLIO
  "result": str | None,                    # PORTFOLIO
  "daily_topic": str | None,               # DAILY
  "daily_story": str | None,               # DAILY
  "selected_keyword": str | None,
  "selected_title": str | None,
  "selected_strength_ids": list[str] | None,   # 가치입증에서 선택된 강점 ID 목록 (BlogResponseDTO)
  "empathy_statements": list[str] | None,      # 생성된 공감 문구 / 핵심 포인트
  "intro_text": str | None,
  "image_recommendations": [{"label": str, "reason": str}] | None,
  "used_images": list[dict] | None,            # composite_url, layout, urls[] (UsedImageDTO)
  "custom_images": list[dict] | None,
  "body_text": str | None,
  "cta_text": str | None,
  "conversion_url": str | None,
  "transform_results": {
    "linkedin": {"post_text": str, "hashtags": list[str]} | None,
    "youtube": {"post_text": str, "hashtags": list[str]} | None,
  } | None,
}
```

---

## Step 1: 유형 선택 + 정보 수집

**참조**: `reference/blog-types.md`

### 동작

1. 사용자에게 블로그 유형 4가지를 제시한다:
   - 1) 정보제공용 (INFO)
   - 2) 자사홍보용 (PURCHASE)
   - 3) 포트폴리오 (PORTFOLIO)
   - 4) 일상글 (DAILY)

2. 선택된 유형에 따라 `reference/blog-types.md`의 수집 질문을 순서대로 묻는다.

3. **공통 수집** (모든 유형):
   - 회사명 (`company_name`)
   - 회사가 하는 일 (`company_service`)
   - 강점 1~3개 (각각 제목 + 한 줄 설명) — 선택 사항

   #### 회사 정보 자동 조회 (MCP 사용 가능 시)
   `bonda:get_my_company` 도구가 사용 가능하면 수동 입력 대신 자동 조회를 우선 시도한다.
   - 허용 계정 alias: `"demodev"` (demodev@demodev.io), `"jocoding"` (contact@jocodingax.ai).
   - 사용자에게 어느 계정을 쓸지 묻고 `bonda:get_my_company(account=...)` 호출.
   - 결과의 `name`을 `company_name`, `service`를 `company_service`, `strengths`를 그대로 `blog_context.strengths`에 채운다.
   - `success=False` 또는 환경변수 누락 시 자동으로 수동 입력으로 폴백한다.
   - 두 alias 외 계정은 지원하지 않으며, 다른 계정을 요청하면 거절하고 수동 입력을 안내한다.

4. **유형별 추가 수집** (`reference/blog-types.md` 참조):
   - INFO: `user_provided_info` (전달할 핵심 정보)
   - PURCHASE: `target_audience`, `target_problem`, `target_desired_outcome`
     - ⚠️ **`target_desired_outcome` 질문 시 반드시 강조**: "글을 읽고 난 직후의 마음 상태(예: '문의해야겠다')가 아니라, **내 서비스/제품을 실제로 이용·체험한 뒤** 사용자가 어떻게 변화하는지" 묻는다. 사용자가 "글을 읽고 ~할 것 같다" 식으로 답하면 다시 물어 서비스 이용 후 변화로 교정한다.
   - PORTFOLIO: `customer_problem`, `solution`, `result`
   - DAILY: `daily_topic` (소주제 선택), `daily_story`

5. Step 1 완료 후 → **Limbic 분석** 실행 (DAILY 제외)

---

## Limbic 분석 (Step 1 완료 직후, DAILY 제외)

**참조**: `reference/limbic-types.md`

### 동작

1. 수집된 정보(blog_type + target_problem 또는 user_provided_info)를 기반으로 독자의 심리 유형을 판단한다.
2. 반드시 하나의 유형만 선택 (혼합 불가):
   - `traditionalist` (전통주의자): 불안 회피, 검증된 것 선호
   - `performer` (실행가): 지위, 성과, 속도 중시
   - `hedonist` (쾌락주의자): 새로움, 재미, 트렌드 추구
   - `disciplinarian` (규율숭배자): 수치, ROI, 체계 중시
3. 판단 결과를 사용자에게 간략히 알리고 (`limbic_type` + 판단 근거 1문장) Step 2로 진행한다.
4. DAILY 유형: 분석 생략, `limbic_type = None`으로 설정.

---

## Step 2: 키워드 추천

**참조**: `reference/customer-journey.md`

본다 백엔드(`back/src/agents/keyword/`)의 4-노드 LangGraph 흐름을 그대로 수행한다. Claude가 LLM 노드(generate_user_thought, convert_to_keywords, select_keywords) 역할을 직접 수행하고, naver API 호출은 `bonda:get_keywords` MCP 도구로 처리한다.

### 동작

1. **Stage 결정** — `blog_type`에 따라 실행할 단계 ID 목록 선택:
   - INFO → `["info_search", "solution_search"]` (정보탐색 카테고리)
   - PURCHASE / PORTFOLIO → `["provider_search", "review_compare"]` (구매직전 카테고리)
   - DAILY → **Step 2 생략**, 바로 Step 3로 이동

2. **각 stage별로 4-노드 순차 수행** (stages는 병렬 가능):

   **🅐 generate_user_thought** — 해당 stage에서 고객이 어떤 생각/행동을 하는지 2~4문장으로 묘사.
   - 입력: `stage_id`, `blog_type`, `my_service`, 타입별 컨텍스트
     - INFO → `user_provided_info`
     - PURCHASE → `target_problem`
     - PORTFOLIO → `portfolio_customer_problem` + `solution` + `result`
   - 규칙:
     - 고객은 **아직 결론(해결책/사례)을 모르는 상태**로 묘사
     - 실제 검색창에 무엇을 입력할지 암시 ("~을 검색한다", "~를 알아본다")
     - 비교·고민·선택 과정 포함
   - 참조: `reference/customer-journey.md`의 stage별 user_thought 예시

   **🅑 convert_to_keywords** — user_thought를 검색 키워드 5~7개로 변환.
   - 규칙:
     - **2~3단어**, 공백 없이 붙여서 (네이버 API 제약)
     - 일반인이 검색창에 실제 입력할 패턴 ("추천", "비용", "방법", "후기", "비교", "순위")
     - `my_service` 도메인에 맞는 키워드만
     - 수식어(맞춤형/전문/고급 등) 금지
   - 출력: `["키워드1", "키워드2", ..., "키워드5~7"]`

   **🅒 call_naver_api** — 변환된 키워드를 hint로 `bonda:get_keywords` 호출하여 연관 키워드와 검색량 조회.
   - 첫 호출: `bonda:get_keywords(hint_keywords=["키워드1"])` (인덱스 0부터)
   - 결과 없거나 부족하면 다음 키워드로 (인덱스 +1)
   - 검색량 20 미만은 자동 필터링됨

   **🅓 select_keywords** — naver API 결과 후보에서 의미 있는 키워드만 AI(Claude)로 선별.
   - **선택 규칙**:
     1. 카테고리(정보탐색/구매직전) 목적에 부합
     2. `my_service`와 관련된 것만
     3. 비슷한 의미의 키워드는 중복 선택 금지 (예: "AI기업"·"AI회사" → 1개만)
     4. 너무 일반적인 키워드 제외 (단일 용어 "다이어트", "운동" 등)
     5. 경쟁 서비스/제품 키워드 제외
   - **has_good_keywords 판단**:
     - `true`: 검색 의도를 정확히 반영 키워드 3개 이상 / `my_service`를 직접 연상시키는 키워드 존재 / 카테고리에 완벽히 부합 키워드 3개 이상
     - `false`: 너무 일반적 / 더 좋은 후보 가능성 / 선택 1개 이하
   - **조기 종료**: 누적 좋은 키워드 ≥ 3개 AND `has_good_keywords=true` → 해당 stage 종료
   - 부족하면 인덱스 +1로 🅒부터 반복 (검색 키워드 모두 소진 시 종료)

3. **결과 통합** — 모든 stage 결과를 합쳐 키워드 중복 제거 후 검색량(monthly_pc + monthly_mobile) 내림차순 정렬.

4. **사용자에게 표 형식으로 제시**:
   ```
   | 키워드 | 월 PC 검색량 | 월 모바일 검색량 | 합계 | 경쟁도 |
   ```

5. 사용자가 최종 키워드 1개를 선택. (선택 안 하면 검색량 가장 높은 키워드 자동 선정)

### MCP 미사용 (NAVER_* 환경변수 누락) 시 폴백

`bonda:get_keywords` 호출이 실패하면 🅐 + 🅑 결과(검색량 없는 키워드)만 표로 제시. 검색량 컬럼은 `-`로 표기.

---

## Step 3: 제목 생성

**참조**: `reference/prompts/title.md`

본다 백엔드(`back/src/agents/title/title_chain.py`)의 공식별 병렬 호출을 그대로 수행한다. 후보를 일부만 추리지 않고 **본다와 동일한 개수**의 제목을 생성한다.

### 동작

1. **공식 목록 결정** (blog_type 별):
   - **INFO / PURCHASE**: 6공식 모두 사용 — `상식 파괴`, `추상어의 저주`, `금지와 위협`, `자아 흠집내기`, `권위자 이용하기`, `뭐야 이게?`
     - 각 공식당 제목 **3개씩 생성** → **총 18개**
   - **PORTFOLIO**: 3공식만 사용 — `상식 파괴`, `추상어의 저주`, `권위자 이용하기`
     - 각 공식당 3개씩 → **총 9개**
   - **DAILY**: 단일 프롬프트 (`DAILY_SYSTEM_PROMPT`) — 키워드 없이, 감성/위트/일기체 톤 각 2개 → **총 6개**

2. **프롬프트 조립** (각 공식별):
   - `BASE_SYSTEM_PROMPT` (카피라이팅 핵심 원칙 + `{formula_section}` 치환)
   - + 유형별 지시사항: `INFO_PURCHASE_INSTRUCTIONS` (INFO/PURCHASE) 또는 `PORTFOLIO_INSTRUCTIONS` (PORTFOLIO)
   - + INFO/PURCHASE에는 `COPYWRITING_TIPS` 추가 (제목 첫/끝 표현, 조합 예시)
   - + `limbic_guide` (limbic_type 기반)
   - DAILY는 BASE와 별개 단일 프롬프트

3. **공통 규칙**:
   - **글자수**: 공백 제외 순수 글자수 **29자 미만**, 띄어쓰기는 반드시 올바르게
   - **키워드 배치**: 3개 중 2개는 키워드를 맨 앞에, 1개는 다른 위치 또는 변형
     - DAILY 예외: 키워드 없으므로 30자 이내 자연스러운 일상 톤
   - **회사 강점 활용** (INFO/PURCHASE): 공식별 3개 중 최대 1개만 회사 강점 사용, 나머지는 공식 자체의 매력으로
   - **가짜 권위 금지**: "구글 출신", "삼성 출신" 같은 없는 경력 지어내기 금지
   - **PORTFOLIO 절대 금지**: 사례에 없는 숫자/통계(312%, 127건 등) 지어내기 X, 다른 업종 사례 섞기 X

4. **결과 제시** — 공식별로 그룹화하여 표시:
   ```
   ## 상식 파괴
   1. ...
   2. ...
   3. ...

   ## 추상어의 저주
   1. ...
   ...
   ```
   - 공식 간 중복 제목은 자동 제거 (먼저 등장한 공식 우선)

5. 사용자가 1개 선택 또는 수정 요청 가능. 선택 안 하면 가장 매력적인 후보 추천.

6. **거부 시**: 동일 keyword + limbic_type 유지하고 재생성. 최대 3회까지 허용.

---

## Step 4: 도입부 생성 + 이미지 추천

**참조**: `reference/prompts/intro.md`

### 동작

가치입증(`selected_strengths`)는 최대 10개로 제한된다 (`back/src/agents/intro/schema.py:19-23` `max_length=10`).

**병렬 실행 구조**:
- `strengths`가 있으면: 가치입증 + 공감하기 + 이미지 추천 세 작업을 동시(병렬) 수행
- `strengths`가 비어있으면: 가치입증은 건너뛰고 공감하기 + 이미지 추천만 병렬 수행
- DAILY 유형: 아래 "DAILY 분기" 참고

1. 공감 문단 + 가치입증 구조로 도입부를 작성한다.
2. `limbic_type`에 맞는 공감 방식 적용 (`reference/prompts/intro.md` 참조).
3. 수집된 `strengths`를 자연스럽게 녹여넣는다.
4. 유형별 공감(empathy) 개수:
   - PURCHASE: 독백형 공감 문구 **7개**
   - INFO: 핵심 정보 포인트 **5개**
   - PORTFOLIO: 고객 후기 인용구 **5개**
   - DAILY: 핵심 포인트 **3개** (30~50자, 가치입증·이미지 추천 생략)
5. 결과물을 사용자에게 보여주고 수정 의견 수렴.

### DAILY 분기

DAILY 유형은 일상 스토리에서 핵심 포인트 3개(30~50자)를 추출한다. 가치입증·이미지 추천은 생략한다.
원본: `back/src/agents/intro/prompts/daily.py` — 출력 형식: `{"empathy_statements": ["문장1", "문장2", "문장3"]}`

### 이미지 추천 (도입부 확정 후, DAILY 제외)

도입부가 확정되면 본문에 들어갈 이미지를 추천한다. DAILY 유형은 이미지 추천을 생략한다.

1. 수집된 정보(`blog_type`, `keyword`, `selected_title`, 유형별 추가 정보)를 종합 분석하여 **최소 1개, 최대 5개** 이미지를 추천한다 (`back/src/agents/intro/schema.py:36-40`).
2. 각 추천은 아래 형식으로 제시:
   - `label`: 구체적인 이미지 설명 (예: "시공 전/후 비교 사진", "상담 진행 중인 모습")
   - `reason`: 독자 관점에서 왜 효과적인지 (예: "독자가 변화를 한눈에 확인할 수 있어 설득력이 높아집니다")
3. **추천 기준**:
   - 독자가 글의 내용을 더 잘 이해할 수 있는 이미지
   - 글의 신뢰도를 높이는 실제 사진·데이터
   - 스크롤을 멈추게 하는 시각적 임팩트
   - 블로그 목적(정보 전달 / 구매 유도 / 신뢰 구축)에 부합
4. **블로그 유형별 방향**:
   - INFO: 정보를 시각적으로 보여주는 이미지 (비교표, 과정 사진, 예시 사진)
   - PURCHASE: 제품/서비스의 품질과 신뢰를 보여주는 이미지 (작업 현장, 결과물, 팀 사진)
   - PORTFOLIO: 실제 프로젝트 결과를 보여주는 이미지 (전/후 비교, 완성 사진, 고객 후기 캡처)
5. **중복 방지**: 강점(`strengths`)에 이미 이미지가 등록된 항목과 중복되는 이미지는 추천하지 않는다.
6. 추천 결과를 `image_recommendations`에 저장하고 사용자에게 표로 보여준다.
7. 사용자에게 "추천된 이미지를 준비해주세요. 본문 생성 시 이미지 위치를 자동 배치합니다."라고 안내한 후 Step 5로 진행.

---

## Step 5: 본문 생성 + 이미지 배치

**참조**: `reference/prompts/body.md`

### 동작

1. `blog_type`에 맞는 본문 구조를 적용한다 (`reference/prompts/body.md` 참조).
2. `limbic_type`에 맞는 문체와 톤 적용.
   - `None` (DAILY): 문체 제약 없음, 자연스럽고 따뜻한 어조.
3. 3단계 문제해결 프레임워크 적용 (위험인식 → 행동촉구 → 해결책+PREP).
   - **DAILY 예외**: BASE_PROMPT 미상속(독립 시스템 프롬프트), 3단계 프레임워크·PREP 미적용, 림빅 가이드 미주입.
4. 강점(strengths)을 본문 전체에 분산 배치.
5. 해시태그 5~10개 본문 마지막에 추가.
6. **글자수 기준**:
   - PURCHASE: 공백 제외 2,500자 이내
   - DAILY: 2,000~3,000자 (`back/src/agents/body/prompts/daily.py:29`)
   - 기타 유형: 적절한 길이 (블로그 가독성 기준)

### 이미지 플레이스홀더 배치

Step 4에서 추천한 이미지가 있으면 본문의 적절한 위치에 플레이스홀더를 삽입한다.

1. `image_recommendations`의 각 항목을 본문 흐름에 맞는 위치에 배치한다.
2. 플레이스홀더 형식: `{{image:이미지ID}}` (예: `{{image:시공전후비교사진}}`)
3. **배치 원칙**:
   - 이미지가 설명하는 내용의 **직후**에 배치 (독자가 텍스트를 읽고 이미지로 확인하는 흐름)
   - 한 섹션(h2/h3 블록)에 이미지를 2개 이상 연속 배치하지 않는다
   - 도입부 직후, CTA 직전에는 배치하지 않는다
4. 추천된 이미지 전부를 사용할 필요는 없다 — 본문 흐름에 자연스러운 것만 배치.
5. DAILY 유형이나 `image_recommendations`가 비어있으면 플레이스홀더 없이 본문만 생성.

---

## Step 6: CTA 생성

**참조**: `reference/prompts/cta.md`

### 동작

1. `limbic_type`에 맞는 CTA 스타일 적용 (`reference/prompts/cta.md` 참조).
2. CTA 공식 3가지 중 하나만 선택 (능력한계치 인정 / 희소성 / 인기성).
3. 진심 어린 약속 문구 포함 (겸손하고 압박감 없이).
4. 2~3문장으로 간결하게 작성.
5. DAILY (`limbic_type = None`): 기본 따뜻한 마무리 CTA.

### CTA 버튼 카피 설정 (카테고리 규칙 기반, 조코딩AX 전용)

CTA 본문을 확정한 뒤, **버튼 문구는 임의로 짓지 말고** 규칙 파일에서 카테고리별로 정해진 카피를 그대로 사용한다.

**참조**: `~/Desktop/dev/blog-image/cta-config.md` (카테고리별 CTA 카피·색상 SSOT)

1. 블로그 **카테고리**를 4개 중 1개로 사용자에게 확인받는다. (Step 6.5 썸네일과 동일 축 — 여기서 확정하면 6.5에서 재사용)
2. 확정된 카테고리에 매핑된 버튼 카피를 `cta-config.md` 규칙대로 적용한다:

   | 카테고리 | 버튼 카피 | 버튼색 / 텍스트색 |
   |---|---|---|
   | AX 인사이트 | `AX진단받기` | `#6B46C1` / `#FFFFF5` |
   | 도입 사례 | `시스템 견적 받기` / `기업 도입 문의` (A/B 교차) | `#F97316` / `#FFFFF5` |
   | AI 도구·가이드 | `AI도입문의` | `#172554` / `#FFFFF5` |
   | 기업교육 소식 | `기업교육 상담 신청` | `#1D4ED8` / `#FFFFF5` |

3. 도입 사례는 두 카피를 **A/B로 교차 사용**한다. (사용자가 A/B 중 하나를 지정하면 그대로 확정)
4. 버튼의 착지 URL은 Step 7에서 생성하는 전환 추적 숏링크를 연결한다.
5. 규칙 파일이 없거나 MCP 미사용 시: `reference/prompts/cta.md`의 `limbic_type` 기반으로 버튼 카피를 생성하되, 조코딩AX 도메인이면 규칙 파일 우선.

> ⚠️ 카피·색상은 규칙 파일(SSOT)이 진실 원천이다. 값이 바뀌면 이 표가 아니라 `cta-config.md`를 따른다.

---

## Step 6.5: 썸네일 생성 (선택)

CTA까지 확정되면 발행 전에 **대표 썸네일**을 만든다. 썸네일은 두 양식이 있으며,
**배경이미지형(실사 풀배경 V2)을 기본·우선 양식으로 고정**한다.

### 양식 우선순위 (고정)

**① [기본] 배경이미지형 — 실사 풀배경 V2 템플릿**
- 템플릿: `~/Desktop/file/jocodingax/블로그자료/_썸네일템플릿_실사/thumbnail_template.html` (+ 같은 폴더 `SPEC.md`)
- 실사 사진(현장/인터뷰/제품 목업) 풀배경 위에 어두운 그라데이션 + 카테고리 태그 + 히어로 카피(흰색) 합성.
- 카테고리 태그색(5색): 기업교육 소식 `#0A47C9` / AX 인사이트 `#5333A4` / 도입사례 `#FA6204` / AI 도구·가이드 `#0A1740` / 무료 진단 `#C2255C`
- 히어로 카피: 글 제목 그대로 쓰지 않는다 → 썸네일용 후킹 카피 **18~25자**, 보통 2줄, 전부 흰색(강조색 없음). 추천 시 각 안의 글자수를 세어 표기.
- 고정값 1200×686, Pretendard. 로고 락업·그라데이션·카피블록 규격은 `SPEC.md` 준수.
- **배경 실사 사진은 사용자에게 받는다.** 저해상도 원본은 SPEC.md의 분할/1배 출력 대응 참고.

**② [요청 시에만] 일러스트형 — 4색 3D 일러스트** (`blog-thumbnail-3color` 스킬)
- ⚠️ **raw 3D 일러스트 생성은 사용자가 명시적으로 요청할 때만 수행한다.** 기본 흐름에서는 raw를 만들지 않는다.

### 동작

1. 사용자에게 썸네일 생성 여부를 물어본다. (불필요하면 건너뛰고 Step 7로)
2. 블로그 **카테고리**를 확인받는다 (태그색 결정). `blog_type`(INFO/PURCHASE/PORTFOLIO/DAILY)과 다른 축이므로 추론 말고 사용자 확인.
3. **기본**: 배경이미지형 V2로 제작 — 사용자 실사 사진 + 히어로 카피(18~25자, 2줄) 합성 → `bonda-use/thumbnail/{N}-...png`.
4. 일러스트형(raw 생성)은 **사용자가 요청한 경우에만** `blog-thumbnail-3color`로 진행.
5. 완성된 `thumbnail`을 Step 7 발행 대표 이미지로 쓰고, **글별 통합 폴더(`블로그자료/블로그-{주제}/`)에도 복사**한다.

> 본문 삽입 이미지(Step 4 `image_recommendations`)와 **대표 썸네일**은 별개다. 이 단계는 대표 썸네일 전용.

---

## Step 7: 전환링크 설정 + 발행

**참조**: `templates/blog-output.md`

### 전환링크 설정

발행 전에 전환링크(트래킹 링크)를 설정한다. 전환링크는 블로그 글에서 독자를 전환 페이지(상담 신청, 예약, 구매 등)로 유도하는 추적 가능한 단축 링크다. 생성된 숏링크는 웹 대시보드의 **'링크 설정 > 생성된 링크'** 탭에서 확인·관리할 수 있다.

1. 사용자에게 전환링크를 추가할지 물어본다.
2. **전환링크 추가 시 (MCP 사용 가능)**:
   - **Step A**: `bonda:get_link_presets()` 호출하여 등록된 프리셋 목록을 보여준다.
     - 프리셋이 있으면 목록에서 선택하도록 안내 (프리셋의 URL과 utm_campaign이 자동 적용).
     - 프리셋이 없으면 전환 URL을 직접 입력받는다.
   - **Step B**: 발행할 각 플랫폼별로 `bonda:create_tracking_link()` 호출하여 숏링크를 생성한다.
     - `original_url`: 프리셋 URL 또는 직접 입력한 URL
     - `platform`: 발행 플랫폼 (`"naver"`, `"inblog"`, `"threads"`, `"link_only"`)
     - `blog_title`: 현재 블로그 제목 (`selected_title`)
     - `link_title`: 프리셋 이름 또는 사용자 지정 제목
     - `preset_id`: 프리셋 선택 시 해당 ID
     - `utm_campaign`: 프리셋에서 가져오거나 직접 지정
   - **Step C**: 생성된 숏링크(예: `https://link.bfrnd.co/l/aBc1234`)를 CTA 텍스트 하단에 삽입.
3. **전환링크 추가 시 (MCP 미사용)**: 전환 URL을 직접 입력받아 CTA 텍스트 하단에 원본 URL 그대로 삽입.
4. **전환링크 미추가 시**: CTA 텍스트만으로 발행 진행.
5. DAILY 유형도 전환링크 설정 가능 (선택 사항).

### 인블로그 등록 (권장: CLI로 초안 등록 — 발행과 분리)

조코딩AX 블로그(`blog.jocodingax.ai` = inblog)는 공식 `inblog` CLI로 **초안(비공개)** 을 만들면
슬러그·CTA 버튼·커버 이미지·카테고리 태그·메타를 한 번에 등록할 수 있다. **기본은 발행하지 않고 초안까지만.**
(`bonda:publish_inblog(title, content)`는 제목+본문만 받아 **즉시 발행**되고 슬러그·CTA·커버를 못 붙이므로 폴백용.)

1. **인증 확인**: `inblog auth status` (활성 블로그가 `jocodingax`인지). 토큰 만료 시 사용자가 `inblog auth login --blog jocodingax` 실행(OAuth).
2. **콘텐츠 HTML 변환**: CLI는 HTML을 받는다(`--content-file`). 최종 본문(마크다운)을 HTML로 변환하고, `[이미지: …]` 자리표시자는 제거, `==하이라이트==`는 `**강조**`로 치환. 로컬 이미지 경로를 넣으면 CDN 자동 업로드된다.
3. **초안 생성** (`--published` **붙이지 않음** → 초안):
   ```bash
   inblog posts create \
     --title "{selected_title}" \
     --slug "{글 slug}" \
     --content-file "{통합폴더}/content.html" \
     --image "{대표 썸네일 경로}" \            # 커버 이미지(로컬→CDN)
     --description "{요약}" \
     --meta-title "{메타 타이틀}" --meta-description "{메타 설명}" \
     --cta-text "{카테고리 버튼 카피}" \        # cta-config.md 규칙
     --cta-link "{Step7 추적 숏링크}" \
     --cta-color "{카테고리 버튼색}" --cta-text-color "#FFFFF5"
   ```
   - CTA 카피·색은 **`~/Desktop/blog-image/cta-config.md` SSOT**(예: 도입사례 = `시스템 견적 받기`/`기업 도입 문의`, `#F97316`).
4. **카테고리 태그 등록**: `inblog tags list`로 ID 확인 → `inblog posts add-tags {postId} --tag-ids {id}` (예: 도입사례 = 18266).
5. **미리보기**로 확인(생성 시 preview 링크 자동 출력). 편집 URL: `https://inblog.ai/dashboard/jocodingax/{postId}`.
6. **발행 절대 금지(기본값): 자동 발행하지 않는다.** `inblog posts publish {postId}`는 **사용자가 명시적으로 "발행해"라고 지시할 때만** 실행한다. 그 전까지는 무조건 초안(`published:false`) 유지 — 이미지·인용문·실명 검수 여지 확보. 글을 다 만들었다고 해서, 또는 이전 맥락에서 "발행" 언급이 있었다고 해서 스스로 발행하지 않는다.
7. 발행한 경우에만 `bonda:save_blog_record()`로 대시보드 기록.

> ⚠️ **update 주의(검증 2026-07-08)**: `inblog posts update --content-file`이 **본문(content_html)을 반영하지 않는** 경우가 있다(슬러그·커버·CTA 등 메타는 반영되면서 본문만 구버전으로 남음). 특히 **본문을 대폭 수정**했을 땐 update를 믿지 말고, **① update 후 `inblog posts get {id} --json`의 `content_html`을 금지어·핵심 문구로 실측 검증**하고, **② 반영 안 됐으면 구 초안 `delete` 후 `create`로 재생성**한다. (익명화처럼 PII 제거가 목적이면 구 초안 방치 자체가 리스크이므로 삭제 권장.)

> ⚠️ **draft↔published 콘텐츠 분리 gotcha(검증 2026-07-09)**: 인블로그는 **초안 콘텐츠와 발행 콘텐츠가 분리**돼 있다. **이미 `published:true`인 글에 `update`하면 초안만 바뀌고 발행본(라이브)은 그대로**다 → `get` 직후엔 내용이 보여도 라이브·재조회 시 빈 값으로 나와 "자꾸 지워진다"고 오인한다.
> - **진단 우선순위**: "자꾸 비워진다" 신고 시 크론·오토파일럿·에디터를 의심하기 전에 **`published` 여부부터 확인**. `published:true` + 빈 라이브 = 이 분리 문제(지워진 게 아니라 발행본 미반영).
> - **발행 순서(고정)**: ① 초안 상태에서 본문 채우기(`update`) → ② `get`으로 `content_html` 실측 → ③ **그다음** `inblog posts publish`. publish가 초안→발행본으로 밀어넣는다. **"먼저 발행하고 편집"은 금지**(발행본이 빈 채로 남음).
> - 편집·검수 중에는 **`unpublish`로 초안 전환**해두면 이 분리로 인한 라이브 오염이 원천 차단된다.

### 발행 (bonda MCP 폴백)

1. **Phase 1 (기본)**: 완성 글을 `templates/blog-output.md` 형식으로 마크다운 출력.
   - 선택된 키워드, Limbic 유형, 예상 글자 수를 메타정보로 함께 표시.
   - 전환링크가 설정되었으면 본문 끝에 포함하여 출력.

2. **Phase 2 (MCP 사용 가능 시)**:
   - `bonda:publish_naver(title, content)` — 네이버 블로그 자동 발행
   - `bonda:publish_inblog(title, content)` — 인블로그 자동 발행
   - 전환링크(숏링크)가 설정되었으면 발행 본문에 자동 포함.
   - 발행 실패 시: Phase 1 방식(복사용 텍스트 출력)으로 자동 폴백.
   - **발행 성공 후**: `bonda:save_blog_record()`를 호출하여 대시보드 목록에 기록한다.
     - `blog_type`: blog_context의 blog_type (소문자: "info" | "purchase" | "portfolio" | "daily")
     - `selected_title`: 발행된 제목
     - `selected_keyword`: 선택된 키워드
     - `intro_text`, `body_text`, `cta_text`: 각 텍스트
     - `platform`: 발행 플랫폼 ("naver" | "inblog" | "linkedin" | "youtube" | "link_only") — 플랫폼별로 각각 호출
     - `post_url`: 발행 결과로 받은 URL
     - 유형별 추가 필드 전달 (target_audience, user_provided_info 등)

---

## Step 8: SNS 변환 (선택사항)

**참조**: `reference/prompts/transform.md`

블로그 발행 후 LinkedIn / YouTube 커뮤니티 탭 후킹 포스트로 변환한다. DAILY를 포함한 모든 블로그 유형에서 사용 가능하다.

### 동작

1. 발행 완료 후 사용자에게 SNS 변환 여부를 물어본다.
   - "LinkedIn · YouTube 커뮤니티 탭 포스트로 변환할 수 있습니다. 원하는 플랫폼을 선택해주세요."

2. **blog_id 확인**: `save_blog_record` 반환값의 `blog_id`를 사용한다.
   - `blog_id`가 없으면 (발행 기록이 저장되지 않은 경우) 변환 불가 → "발행 기록 저장 후 다시 시도해주세요" 안내.

3. **blog_url**: `post_url`(발행 결과 URL)이 있으면 `blog_url`로 전달, 없으면 `None`으로 호출.

4. **MCP 사용 가능 시**:
   - LinkedIn: `bonda:transform_blog_to_linkedin(blog_id=..., blog_url=...)` 호출
     - 결과: `post_text` (300~500자), `hashtags` (3~5개) 표시
   - YouTube: `bonda:transform_blog_to_youtube(blog_id=..., blog_url=...)` 호출
     - 결과: `post_text` (300~500자), `hashtags` (3~5개) 표시
     - **노트**: YouTube는 백엔드가 LinkedIn과 동일한 체인(`linkedin_chain_runner`)을 사용하므로 포맷이 LinkedIn과 동일하다 (`blog_transform_service.py:95`).
   - 결과를 `blog_context.transform_results`에 저장.

5. **결과 표시**: 변환된 포스트를 그대로 출력하고 사용자에게 복사하여 직접 발행하도록 안내한다.
   - LinkedIn: 해당 플랫폼에 직접 붙여넣기
   - YouTube: YouTube 스튜디오 커뮤니티 탭에 직접 붙여넣기

6. 여러 플랫폼 변환 시 순차적으로 각각 호출한다.

### MCP 미사용 시 폴백

`bonda:transform_blog_to_*` 호출이 실패하거나 MCP를 사용할 수 없으면,
`reference/prompts/transform.md`의 프롬프트를 그대로 사용하여 Claude가 직접 변환한다.
YouTube 폴백은 LinkedIn 시스템 프롬프트를 그대로 사용한다.

- `blog_context`의 `company_name`, `company_service`, `selected_keyword`, `selected_title`, `body_text`를 입력으로 사용.
- `post_url`이 있으면 `blog_url`로 사용, 없으면 "URL 없음"으로 대체.

---

## 단계별 참조 파일 요약

| 단계 | 참조 파일 |
|------|-----------|
| Step 1 (정보 수집) | `reference/blog-types.md` |
| Limbic 분석 | `reference/limbic-types.md` |
| Step 2 (키워드) | `reference/customer-journey.md` |
| Step 3 (제목) | `reference/prompts/title.md` |
| Step 4 (도입부 + 이미지 추천) | `reference/prompts/intro.md` |
| Step 5 (본문 + 이미지 배치) | `reference/prompts/body.md` |
| Step 6 (CTA) | `reference/prompts/cta.md` |
| Step 6.5 (썸네일, 선택) | `blog-thumbnail-3color` 스킬 |
| Step 7 (전환링크 + 발행) | `templates/blog-output.md` |
| Step 8 (SNS 변환) | `reference/prompts/transform.md` |

---

## 엣지 케이스 처리

| 상황 | 처리 |
|------|------|
| DAILY 유형 | Limbic 분석 생략, Step 2 생략, 이미지 추천 생략, limbic_type = None |
| 강점 미입력 | 건너뛰기 허용, 도입부/본문 강점 항목 생략 |
| 키워드 검색량 20 미만 | naver API에서 자동 필터링됨, 다음 검색 키워드(인덱스 +1)로 진행 |
| 키워드 stage별 좋은 키워드 3개 미달 | 모든 검색 키워드 소진할 때까지 인덱스 +1 반복 |
| 제목 거부 | 동일 keyword + limbic_type 유지, 최대 3회 재생성 |
| 이미지 추천 건너뛰기 | 사용자가 이미지 불필요하다고 하면 생략, 본문에 플레이스홀더 없이 진행 |
| 전환링크 미설정 | 사용자가 불필요하다고 하면 생략, CTA 텍스트만으로 발행 |
| 프리셋 없음 | 프리셋 목록이 비어있으면 URL 직접 입력으로 진행 |
| 숏링크 생성 실패 | 원본 URL을 그대로 삽입하여 폴백 |
| 로그인 실패 (BONDA_EMAIL/PASSWORD) | 에러 메시지 표시 + 원본 URL 폴백 안내 |
| 네이버 발행 실패 | 복사용 마크다운 출력으로 폴백 |
| 환경변수 누락 (Phase 2) | 명확한 에러 메시지 + Phase 1 폴백 안내 |
| 힌트 키워드 5개 초과 | 앞 5개만 사용 (Naver API 제한) |
| blog_id 없음 (record 미저장) | transform 불가, save_blog_record 후 다시 시도 안내 |
| LinkedIn/YouTube 변환 실패 | reference/prompts/transform.md 프롬프트로 Claude 직접 변환 폴백 |
