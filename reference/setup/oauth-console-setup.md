# OAuth 콘솔 설정 절차 (Google / Kakao / Naver)

> Auth.js v5(NextAuth) 소셜 로그인 3종. redirect URI base는 env `AUTH_URL`.
> 콜백 경로는 Auth.js 규약: `{AUTH_URL}/api/auth/callback/{provider}`.
> **로컬·프로덕션 redirect를 둘 다 등록**하는 것이 핵심 함정 회피 포인트.
> 콘솔 UI 라벨은 자주 바뀌므로 "~ 찾기"로 기술.

공통 준비:
- `AUTH_SECRET` = `openssl rand -base64 32` 결과.
- `AUTH_URL` = 로컬 `http://localhost:3000`, 프로덕션은 실제 도메인.
- `AUTH_TRUST_HOST=true` (엣지/프록시 환경).

---

## 1. Google — Google Cloud Console
콜백: `{AUTH_URL}/api/auth/callback/google`

1. https://console.cloud.google.com → 프로젝트 생성(또는 선택).
2. **OAuth 동의 화면(OAuth consent screen)** 찾기 → User Type 지정(외부),
   앱 이름·지원 이메일·개발자 연락처 입력. 게시 상태가 "테스트"면 테스트 사용자에 본인 추가.
3. **사용자 인증 정보(Credentials)** → "사용자 인증 정보 만들기" → **OAuth 클라이언트 ID** 찾기.
4. 애플리케이션 유형 = **웹 애플리케이션**.
5. **승인된 리디렉션 URI**에 둘 다 등록:
   - `http://localhost:3000/api/auth/callback/google`
   - `https://<프로덕션도메인>/api/auth/callback/google`
6. 발급된 값 → `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`.
7. scope: 기본 `openid email profile`이면 충분(Auth.js Google provider 기본).

## 2. Kakao — Kakao Developers
콜백: `{AUTH_URL}/api/auth/callback/kakao`

1. https://developers.kakao.com → **애플리케이션 추가** 찾기.
2. **플랫폼** 설정에서 사이트 도메인(로컬/프로덕션) 등록.
3. **카카오 로그인** 활성화 → **Redirect URI** 에 둘 다 등록:
   - `http://localhost:3000/api/auth/callback/kakao`
   - `https://<프로덕션도메인>/api/auth/callback/kakao`
4. **앱 키**에서 REST API 키 → `KAKAO_CLIENT_ID`.
   `KAKAO_CLIENT_SECRET` = 보안(Client Secret) 메뉴에서 발급·**사용함(ON)** 처리한 값.
5. **동의 항목(scope)**:
   - 닉네임/프로필은 기본 동의 가능.
   - ⚠️ **이메일·전화번호는 비즈앱 전환 + 검수 전까지 제공되지 않을 수 있다.**
     이메일 없이 가입을 받아야 하면 코드가 이를 허용해야 함.
   - env `OAUTH_REQUEST_CONTACT`:
     - `false` → 이메일/전화 동의를 **필수로 요구하지 않음**(비즈앱 검수 전 기본값).
     - `true` → 이메일·전화 필수 동의를 요청(비즈앱 검수 통과 후에만 켤 것).

## 3. Naver — Naver Developers
콜백: `{AUTH_URL}/api/auth/callback/naver`

1. https://developers.naver.com → **Application 등록** 찾기.
2. 사용 API = **네이버 로그인** 선택, 제공 정보(이메일/이름 등) 지정.
3. **서비스 URL** + **Callback URL** 에 둘 다 등록:
   - `http://localhost:3000/api/auth/callback/naver`
   - `https://<프로덕션도메인>/api/auth/callback/naver`
4. 발급 값 → `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`.
5. ⚠️ 네이버 로그인은 **검수(검토) 절차** 후 일반 사용자에게 공개된다. 검수 전에는
   등록한 개발자 계정으로만 로그인 가능.

---

## 흔한 함정 요약
- **redirect_uri_mismatch**: 콘솔에 등록한 URI와 실제 콜백 URL의 http/https·trailing slash·
  포트가 한 글자라도 다르면 실패. 로컬·프로덕션 둘 다 등록했는지 먼저 확인.
- 프로덕션 배포 후 `AUTH_URL`만 바꾸고 콘솔 redirect 추가를 잊음 → 운영에서 로그인 깨짐.
- 카카오: 이메일이 안 와서 가입 INSERT가 실패 → `OAUTH_REQUEST_CONTACT=false`로 두고
  이메일 없는 사용자 흐름을 코드가 처리하는지 점검.
- Client Secret 미발급/미사용 상태 → 일부 provider에서 인증 실패.
