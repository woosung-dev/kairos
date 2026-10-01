// SCR-001 오프라인 화면 — SW 가 내비게이션 네트워크 실패 때만 돌려주는 HTML 1장
// (docs/requirements/pwa.md §4.4).
//
// ★외부 요청 0 — 이미지·폰트·스크립트 파일을 참조하지 않는다. 오프라인이라 받을 수 없다.
//   폰트도 CDN(Satoshi·Pretendard)을 못 쓰므로 시스템 스택이다.
// ★색은 DESIGN.md Dark 토큰 hex 고정 — 앱 CSS 변수를 읽을 수 없는 독립 문서다.
// ★캐시하지 않는다. 별도 /offline 라우트·precache 가 없고, 이 문자열이 SW 번들에 들어 있다.
// ★아이콘은 `data:` URL 로 문서 안에 둔다 — 아이콘 선언이 없으면 headed Chrome 이 화면을 그릴 때마다
//   `/favicon.ico` 를 요청하고, 오프라인이라 console.error 1건이 남는다 (headless 는 요청하지 않아
//   e2e 가 못 잡는다, pwa.md §4.4 · EVAL-IMPL-1 D2).

export const OFFLINE_TITLE = "오프라인 — Kairos";

// K 모노그램 축약판 — 외부 폰트 없이 sans-serif bold. 색은 DESIGN.md Dark accent / bg.
const OFFLINE_ICON_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">' +
  '<rect width="32" height="32" rx="6" fill="#0A0A0B"/>' +
  '<text x="16" y="23" text-anchor="middle" font-family="sans-serif" font-weight="700" font-size="20" fill="#3ECFB4">K</text>' +
  "</svg>";

// encodeURIComponent 로 `#`·`"`·`<`·`>` 를 전부 이스케이프한다 — href 속성·URL 파서 어느 쪽에서도 안 깨진다.
const OFFLINE_ICON_HREF = `data:image/svg+xml,${encodeURIComponent(OFFLINE_ICON_SVG)}`;

export const OFFLINE_HTML = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0A0A0B">
<title>${OFFLINE_TITLE}</title>
<link rel="icon" href="${OFFLINE_ICON_HREF}">
<style>
  *, *::before, *::after { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    background: #0A0A0B;
    color: #EDEDEF;
    font-family: -apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Pretendard", sans-serif;
    -webkit-font-smoothing: antialiased;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px max(16px, env(safe-area-inset-right, 0px)) 24px max(16px, env(safe-area-inset-left, 0px));
  }
  main {
    width: 100%;
    max-width: 360px;
    background: #141416;
    border: 1px solid #2A2A2E;
    border-radius: 6px;
    padding: 32px 24px;
    text-align: center;
  }
  .mark {
    width: 48px;
    height: 48px;
    margin: 0 auto 20px;
    border-radius: 6px;
    border: 1px solid #2A2A2E;
    background: #0A0A0B;
    color: #3ECFB4;
    font-size: 24px;
    font-weight: 700;
    line-height: 46px;
  }
  h1 { margin: 0 0 8px; font-size: 18px; font-weight: 600; }
  p { margin: 0 0 24px; font-size: 14px; line-height: 1.6; color: #8E8E93; }
  button {
    height: 36px;
    padding: 0 16px;
    border: 0;
    border-radius: 6px;
    background: #3ECFB4;
    color: #0A0A0B;
    font: inherit;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
  }
  button:focus-visible { outline: 2px solid #EDEDEF; outline-offset: 2px; }
</style>
</head>
<body>
<main data-testid="offline-screen">
  <div class="mark" aria-hidden="true">K</div>
  <h1>인터넷에 연결되어 있지 않아요</h1>
  <p>연결되면 자동으로 다시 불러옵니다. 오프라인에서는 회의·노트를 볼 수 없어요.</p>
  <button type="button" data-testid="offline-retry">다시 시도</button>
</main>
<script>
  document.querySelector('[data-testid="offline-retry"]').addEventListener("click", function () { location.reload(); });
  window.addEventListener("online", function () { location.reload(); });
</script>
</body>
</html>
`;
