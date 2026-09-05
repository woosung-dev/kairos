// README 미리보기 PNG 캡처 — archify HTML 의 다이어그램 svg(범례 포함)만 라이트/다크로 클립한다.
// 사용: node docs/architecture/diagrams/capture-png.mjs <name> [<name> ...]   (apps/web 의 Playwright 를 그대로 쓴다)
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { chromium } = await import(
  path.join(here, '../../../apps/web/node_modules/@playwright/test/index.mjs')
);

const names = process.argv.slice(2);
if (names.length === 0) {
  console.error('usage: node capture-png.mjs <diagram-name> [...]  (예: system-architecture)');
  process.exit(1);
}

const browser = await chromium.launch();
for (const name of names) {
  for (const theme of ['light', 'dark']) {
    const ctx = await browser.newContext({
      viewport: { width: 2200, height: 1400 },
      deviceScaleFactor: 1,
      colorScheme: theme,
    });
    // Viewer 는 localStorage 의 archify-theme 을 첫 페인트 전에 읽는다.
    await ctx.addInitScript((t) => {
      try { localStorage.setItem('archify-theme', t); } catch (_) { /* 무시 */ }
    }, theme);
    const page = await ctx.newPage();
    await page.goto(`file://${path.join(here, `${name}.html`)}`, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    await page.waitForTimeout(600);
    // 뷰어 크롬(PATH/MAP/LENS 도크)은 빼고 svg(범례 포함)만 자른다 — 2026-09-04 PNG 와 같은 프레이밍.
    await page.addStyleTag({ content: '[class*="dock"], .no-print { display: none !important; }' });
    const box = await page.locator('.diagram-container svg').first().boundingBox();
    if (!box) throw new Error(`${name}.html 에서 .diagram-container svg 를 찾지 못했다 — archify deliver 산출물인지 확인`);
    const out = path.join(here, `${name}.${theme}.png`);
    await page.screenshot({
      path: out,
      clip: {
        x: Math.floor(box.x), y: Math.floor(box.y),
        width: Math.ceil(box.width), height: Math.ceil(box.height),
      },
    });
    console.log(`${path.relative(process.cwd(), out)} ${Math.ceil(box.width)}x${Math.ceil(box.height)}`);
    await ctx.close();
  }
}
await browser.close();
