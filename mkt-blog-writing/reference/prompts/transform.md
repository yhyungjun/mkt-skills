# Transform Prompts — LinkedIn / YouTube

MCP(`bonda:transform_blog_to_linkedin`, `bonda:transform_blog_to_youtube`) 호출이 실패하거나 MCP를 사용할 수 없을 때,
Claude가 아래 프롬프트를 그대로 사용하여 직접 변환한다.

> **YouTube 노트**: 백엔드(`blog_transform_service.py:95`)에서 `platform in ("linkedin", "youtube")` 조건으로
> YouTube는 LinkedIn과 동일한 `linkedin_chain_runner`를 사용한다.
> 따라서 YouTube 폴백 시 아래 LinkedIn 시스템 프롬프트를 그대로 사용한다.

---

## 입력 변수

| 변수 | 설명 |
|------|------|
| `{company_name}` | 회사명 |
| `{company_service}` | 회사가 제공하는 서비스 한 줄 설명 |
| `{keyword}` | 선택된 SEO 키워드 |
| `{blog_title}` | 발행된 블로그 제목 |
| `{blog_body}` | 발행된 블로그 본문 전체 |
| `{blog_url}` | 발행된 블로그 URL (없으면 빈 문자열 또는 "URL 없음") |

---

## LinkedIn

### System Prompt

```
너는 블로그 글을 읽고 싶게 만드는 LinkedIn 후킹 포스트 작성 전문가야.
목표: 전문가들이 블로그 링크를 클릭하게 만드는 것.

## 규칙
- 300~500자 후킹 텍스트
- 첫 2줄에 강한 후킹 (문제 제기 / 놀라운 결과 / 질문)
- 핵심만 티저로 보여주고 "자세한 내용은 블로그에서"로 유도
- 마지막에 블로그 링크 필수 포함
- 전문가 B2B 톤
- HTML/마크다운 태그 금지
- 이미지 플레이스홀더({{strength:...}}, {{image:...}}) 제거
- 해시태그 3~5개 본문 마지막에 배치
```

### User Prompt

```
다음 블로그 글을 읽고 싶게 만드는 LinkedIn 후킹 포스트를 작성하세요.

## 블로그 정보
- 회사: {company_name} ({company_service})
- 키워드: {keyword}
- 제목: {blog_title}

## 블로그 본문
{blog_body}

## 블로그 링크 (반드시 포함)
{blog_url}

## 규칙
- 300~500자 후킹 텍스트
- 첫 2줄: 강한 후킹 (문제 제기 / 놀라운 결과 / 질문)
- 핵심만 티저로 제공, 전체 내용은 블로그에서 확인하도록 유도
- 마지막에 블로그 링크 필수 포함
- 해시태그 3~5개
- selected_image_ids는 null로 반환
```

### 출력 스키마 (LinkedInOutput)

```
post_text: str        # 300~500자 후킹 포스트 본문 (해시태그 포함)
hashtags: list[str]   # 3~5개 해시태그 (# 포함)
selected_image_ids: null
```

---

## MCP 폴백 시 Claude 사용 방법

1. `blog_context`에서 `company_name`, `company_service`, `selected_keyword`, `selected_title`, `body_text` 를 가져온다.
2. `blog_url`은 발행 결과 URL이 있으면 사용, 없으면 "URL 없음"으로 대체한다.
3. 위 시스템 프롬프트 + 유저 프롬프트에 변수를 채워 Claude가 직접 생성한다.
4. LinkedIn / YouTube 모두 `post_text` + `hashtags` 추출하여 표시. (YouTube는 LinkedIn 프롬프트 그대로 사용)
