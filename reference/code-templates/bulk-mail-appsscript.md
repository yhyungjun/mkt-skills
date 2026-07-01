# bulk-mail-appsscript — Gmail bulk send with open/click tracking

> Brand-neutral template extracted from `granter-landing` root
> (`send-preorder-email.gs` + `buildHtmlBody.gs`).
> Snapshot: 2026-06-11. Runs in Google Apps Script (Gmail + Drive + UrlFetch).
> Replace every `__PLACEHOLDER__` token.
>
> ⚠️ SECURITY — secret separation is MANDATORY.
> The **original** `send-preorder-email.gs` hardcoded a live Supabase service key
> (`SUPABASE_KEY: "sb_secret_..."`) directly in `CONFIG`. That is a real secret
> leak: anyone with read access to the script gets full DB write access.
> This template is the corrected **safe version** — secrets are read from
> **Script Properties** via `PropertiesService.getScriptProperties()` and never
> appear in source. Non-secret config (URLs, file IDs, campaign name) stays inline.
> If you ever port the original, you MUST move `SUPABASE_KEY` out of source.

## One-time setup (per script)

In the Apps Script editor: **Project Settings → Script Properties** → add:

| Property | Value |
|---|---|
| `SUPABASE_URL` | `https://__PROJECT__.supabase.co` |
| `SUPABASE_KEY` | the Supabase **service role / secret** key (server-side only) |

Everything else (`TRACKING_BASE`, `ZIP_FILE_ID`, `FREE_LECTURE_URL`, `CAMPAIGN`)
is non-secret and stays in `CONFIG`. The tracking endpoints
(`/api/track/open`, `/api/track/click`) live in the Next.js app.

---

## `send-preorder-email.gs` (secret-separated safe version)

PRESERVE: the send loop with per-recipient try/catch + Logger, `registerEmailSend_`
writing an `email_sends` row with a generated UUID before sending, the PostgREST
filters (`is_preorder=eq.true&cohort=eq.__COHORT__&marketing_consent=eq.true`),
ZIP attachment via `DriveApp.getFileById(...).getAs(MimeType.ZIP)`, the
`testSendToSelf` and `checkEmailStats` helpers.
CHANGED vs original: `SUPABASE_URL` / `SUPABASE_KEY` now come from Script
Properties; a `requireProp_` guard fails fast if they are unset.

```js
/**
 * 사전예약자 이메일 발송 스크립트 (Google Apps Script)
 *
 * 사전 준비:
 * 1. Supabase SQL Editor에서 email-tracking-setup.sql 실행 (email_sends / email_events)
 * 2. Google Drive에 첨부 zip 업로드 → 파일 ID를 CONFIG.ZIP_FILE_ID에 입력
 * 3. Project Settings → Script Properties에 SUPABASE_URL / SUPABASE_KEY 등록 (절대 소스에 두지 말 것)
 * 4. 트래킹 API Route 포함 배포 (/api/track/open, /api/track/click)
 * 5. sendPreorderEmails() 실행
 */

// ─── 비밀이 아닌 설정만 인라인 ───
var CONFIG = {
  TRACKING_BASE: "https://__DOMAIN__/api/track",
  ZIP_FILE_ID: "__GOOGLE_DRIVE_FILE_ID__",
  FREE_LECTURE_URL: "https://youtube.com/__FREE_LECTURE__",
  CAMPAIGN: "__CAMPAIGN__" // e.g. "preorder-skill-2026"
};

// ─── 비밀은 Script Properties에서만 읽는다 (소스에 하드코딩 금지) ───
function requireProp_(name) {
  var v = PropertiesService.getScriptProperties().getProperty(name);
  if (!v) {
    throw new Error("Missing Script Property: " + name + " — Project Settings > Script Properties에 등록하세요.");
  }
  return v;
}
function supabaseUrl_() { return requireProp_("SUPABASE_URL"); }
function supabaseKey_() { return requireProp_("SUPABASE_KEY"); }

// ─── 메인 함수 ───
function sendPreorderEmails() {
  var recipients = fetchPreorderRecipients_();
  if (recipients.length === 0) {
    Logger.log("발송 대상 없음");
    return;
  }

  var zipFile = DriveApp.getFileById(CONFIG.ZIP_FILE_ID);
  Logger.log("첨부파일: " + zipFile.getName() + " (" + Math.round(zipFile.getSize() / 1024) + "KB)");

  var subject = "__EMAIL_SUBJECT__";
  var senderName = "__SENDER_NAME__";

  var sentCount = 0;
  for (var i = 0; i < recipients.length; i++) {
    var r = recipients[i];
    try {
      var sendId = registerEmailSend_(r, subject);
      var htmlBody = buildHtmlBody_(r, sendId);

      GmailApp.sendEmail(r.email, subject, "", {
        htmlBody: htmlBody,
        attachments: [zipFile.getAs(MimeType.ZIP)],
        name: senderName
      });

      sentCount++;
      Logger.log("발송 완료: " + r.name + " (" + r.email + ")");
    } catch (e) {
      Logger.log("발송 실패: " + r.email + " - " + e.message);
    }
  }

  Logger.log("총 " + sentCount + "/" + recipients.length + "명 발송 완료");
}

// ─── Supabase에서 사전예약자 조회 ───
function fetchPreorderRecipients_() {
  var url = supabaseUrl_() + "/rest/v1/applications"
    + "?is_preorder=eq.true&cohort=eq.__COHORT__&marketing_consent=eq.true"
    + "&select=id,name,email,phone";

  var key = supabaseKey_();
  var res = UrlFetchApp.fetch(url, {
    headers: {
      "apikey": key,
      "Authorization": "Bearer " + key
    }
  });

  var data = JSON.parse(res.getContentText());
  Logger.log("사전예약자 " + data.length + "명 조회됨");
  return data;
}

// ─── Supabase에 발송 기록 ───
function registerEmailSend_(recipient, subject) {
  var sendId = Utilities.getUuid();
  var url = supabaseUrl_() + "/rest/v1/email_sends";
  var key = supabaseKey_();

  UrlFetchApp.fetch(url, {
    method: "post",
    headers: {
      "apikey": key,
      "Authorization": "Bearer " + key,
      "Content-Type": "application/json",
      "Prefer": "return=minimal"
    },
    payload: JSON.stringify({
      id: sendId,
      application_id: recipient.id,
      recipient_email: recipient.email,
      recipient_name: recipient.name,
      subject: subject,
      campaign: CONFIG.CAMPAIGN
    })
  });

  return sendId;
}

// ─── 테스트: 본인에게만 발송 ───
function testSendToSelf() {
  var zipFile = DriveApp.getFileById(CONFIG.ZIP_FILE_ID);
  var testRecipient = { id: "00000000-0000-0000-0000-000000000000", name: "테스트", email: Session.getActiveUser().getEmail(), phone: "" };
  var sendId = Utilities.getUuid();
  var htmlBody = buildHtmlBody_(testRecipient, sendId);

  GmailApp.sendEmail(testRecipient.email, "[테스트] " + "__EMAIL_SUBJECT__", "", {
    htmlBody: htmlBody,
    attachments: [zipFile.getAs(MimeType.ZIP)],
    name: "__SENDER_NAME__"
  });

  Logger.log("테스트 발송 완료: " + testRecipient.email);
}

// ─── 발송 현황 조회 (open/click 집계) ───
function checkEmailStats() {
  var key = supabaseKey_();
  var headers = { "apikey": key, "Authorization": "Bearer " + key };

  var sendsUrl = supabaseUrl_() + "/rest/v1/email_sends?campaign=eq." + CONFIG.CAMPAIGN + "&select=id,recipient_email,recipient_name,sent_at";
  var sends = JSON.parse(UrlFetchApp.fetch(sendsUrl, { headers: headers }).getContentText());

  var eventsUrl = supabaseUrl_() + "/rest/v1/email_events?select=email_send_id,event_type,created_at";
  var events = JSON.parse(UrlFetchApp.fetch(eventsUrl, { headers: headers }).getContentText());

  Logger.log("=== 발송 현황 ===");
  Logger.log("총 발송: " + sends.length + "건");

  for (var i = 0; i < sends.length; i++) {
    var s = sends[i];
    var opens = events.filter(function(e) { return e.email_send_id === s.id && e.event_type === "open"; }).length;
    var clicks = events.filter(function(e) { return e.email_send_id === s.id && e.event_type === "click"; }).length;
    Logger.log(s.recipient_name + " (" + s.recipient_email + ") — 오픈: " + opens + "회, 클릭: " + clicks + "회");
  }
}
```

---

## `buildHtmlBody.gs` — tracked HTML body (open pixel + click wrap)

Source: `send-preorder-email.gs::buildHtmlBody_` (the richer of the two original
copies; the standalone `buildHtmlBody.gs` was a plainer duplicate).
Replacement points: all body copy + `__TEAM_SIGNATURE__`.

PRESERVE — the tracking mechanics are the whole point:
- **Open pixel**: a 1×1 hidden `<img>` at the bottom pointing to
  `TRACKING_BASE + "/open?id=" + sendId`.
- **Click wrap**: every outbound link is rewritten through
  `TRACKING_BASE + "/click?id=" + sendId + "&url=" + encodeURIComponent(target)`
  so the tracking endpoint logs the click then 302-redirects to the real URL.
- `sendId` is the `email_sends.id` UUID created in `registerEmailSend_`, so opens
  and clicks join back to the recipient.

```js
// ─── HTML 본문 생성 (추적 픽셀 + 클릭 래핑) ───
function buildHtmlBody_(recipient, sendId) {
  var trackOpen = CONFIG.TRACKING_BASE + "/open?id=" + sendId;
  var trackClick = function(url) {
    return CONFIG.TRACKING_BASE + "/click?id=" + sendId + "&url=" + encodeURIComponent(url);
  };

  var freeLectureUrl = CONFIG.FREE_LECTURE_URL;

  return '<!DOCTYPE html>'
    + '<html><head><meta charset="utf-8"></head>'
    + '<body style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;line-height:1.7;color:#222;max-width:600px;margin:0 auto;padding:20px;">'

    + '<p>안녕하세요, <strong>__AUDIENCE__</strong>을 위한 __PRODUCT__입니다.</p>'

    + '<p>사전예약 감사합니다. 약속드린 무료 선물 — <strong>__GIFT_NAME__</strong>을 보내드려요.</p>'

    + '<h3 style="color:#333;margin-top:24px;">뭘 해주냐면,</h3>'
    + '<p>__GIFT_DESC__</p>'

    + '<h3 style="color:#333;margin-top:24px;">시작은 3단계</h3>'
    + '<p style="margin-bottom:4px;">(자세한 건 zip 안 사용법 PDF에 그림으로 담았어요)</p>'
    + '<ol style="padding-left:20px;">'
    + '<li>__STEP_1__ — 처음이시면 <a href="' + trackClick(freeLectureUrl) + '" style="color:#2563eb;">무료 강의</a>부터</li>'
    + '<li>__STEP_2__</li>'
    + '<li>__STEP_3__</li>'
    + '</ol>'

    + '<h3 style="color:#333;margin-top:24px;">그리고 이건 시작일 뿐이에요.</h3>'
    + '<p>__UPSELL_INTRO__</p>'
    + '<ul style="padding-left:20px;">'
    + '<li><strong>__UPSELL_1__</strong></li>'
    + '<li><strong>__UPSELL_2__</strong></li>'
    + '<li><strong>__UPSELL_3__</strong></li>'
    + '</ul>'

    + '<p>__CLOSING__</p>'

    + '<p>감사합니다.<br><strong>__TEAM_SIGNATURE__</strong></p>'

    + '<img src="' + trackOpen + '" width="1" height="1" style="display:none" alt="" />'
    + '</body></html>';
}
```

---

### Tracking endpoints (Next.js side — for reference)

The Apps Script only emits the tracked URLs. The matching routes live in the app:
`app/api/track/open/route.ts` (logs `open` event, returns 1×1 pixel) and
`app/api/track/click/route.ts` (logs `click` event, redirects to `?url=`).
Both insert into the `email_events` table keyed by `email_send_id = id`.
