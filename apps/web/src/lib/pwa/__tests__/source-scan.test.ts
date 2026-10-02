// 소스 스캔 — CI 에서 결정적으로 도는 정적 가드
// - T-PWA-12 ※1: lib/pwa/ 에 내비게이션 프리로드 API 이름 0건 (pwa.md C-23)
// - T-PWA-10 소스 부분: apps/web/src 에 Cache Storage·IndexedDB 열기 0건 (pwa.md C-4)
// - pwa.md C-3: SW 등록 호출부는 레포 전체에서 정확히 1곳
// - pwa.md C-28: sw.ts 와 그 상대 import 그래프에 Node 전역 식별자 0건 — worker 번들은 env 를
//   인라인하지 않아 남은 참조가 빌드 panic 이 된다. 주석에도 쓰지 않는다 (전체 텍스트 검사).
//
// ★금지 문자열은 조각을 이어 붙여 만든다 — 이 파일 자체가 스캔에 걸리지 않게.
//   정규식 `a|b` 대신 문자열을 하나씩 includes 로 본다 (test-matrix ※1).
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const SRC_ROOT = path.resolve(__dirname, "../../..");
const PWA_DIR = path.resolve(__dirname, "..");
const THIS_FILE = path.resolve(__filename);

function listSourceFiles(dir: string): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      files.push(...listSourceFiles(full));
    } else if (/\.(?:ts|tsx|js|mjs)$/.test(entry) && full !== THIS_FILE) {
      files.push(full);
    }
  }
  return files;
}

// 정적 import·export-from·side-effect import·dynamic import 의 모든 지정자
const ANY_IMPORT =
  /(?:import|export)\s[^'"]*?from\s*["']([^"']+)["']|import\s*["']([^"']+)["']|import\(\s*["']([^"']+)["']\s*\)/g;

const RELATIVE_IMPORT = /(?:import|export)\s[^'"]*?from\s*["'](\.{1,2}\/[^"']+)["']|import\s*["'](\.{1,2}\/[^"']+)["']/g;

/** entry 에서 시작해 상대 경로 import·export-from 을 따라간 파일 목록 (entry 포함). */
function collectRelativeImportGraph(entry: string): string[] {
  const seen = new Set<string>();
  const visit = (file: string) => {
    if (seen.has(file)) return;
    seen.add(file);
    for (const match of readFileSync(file, "utf-8").matchAll(RELATIVE_IMPORT)) {
      const specifier = match[1] ?? match[2];
      const base = path.resolve(path.dirname(file), specifier);
      const resolved = [base, `${base}.ts`, `${base}.tsx`, path.join(base, "index.ts")].find(
        (candidate) => {
          try {
            return statSync(candidate).isFile();
          } catch {
            return false;
          }
        }
      );
      if (!resolved) throw new Error(`해석 실패: ${specifier} (${file})`);
      visit(resolved);
    }
  };
  visit(entry);
  return [...seen];
}

function filesContaining(files: string[], needle: string): string[] {
  return files.filter((file) => readFileSync(file, "utf-8").includes(needle));
}

describe("source scan", () => {
  it("lib/pwa/ 에 navigation" + "Preload·preload" + "Response 가 없다", () => {
    const files = listSourceFiles(PWA_DIR);
    expect(files.length).toBeGreaterThan(0);
    for (const needle of ["navigation" + "Preload", "preload" + "Response"]) {
      expect(filesContaining(files, needle), needle).toEqual([]);
    }
  });

  it("src 에 Cache Storage·IndexedDB 열기가 없다", () => {
    const files = listSourceFiles(SRC_ROOT);
    for (const needle of ["caches" + ".open", "indexedDB" + ".open"]) {
      expect(filesContaining(files, needle), needle).toEqual([]);
    }
  });

  it("sw.ts 와 그 상대 import 그래프에 Node 전역 식별자가 없다 (pwa.md C-28)", () => {
    const graph = collectRelativeImportGraph(path.join(PWA_DIR, "sw.ts"));
    // 공허 통과 방지 — 그래프가 실제로 따라갔는지 본다.
    expect(graph.map((file) => path.relative(PWA_DIR, file))).toEqual(
      expect.arrayContaining(["sw.ts", "navigation.ts", "offline-page.ts", "sw-types.ts"])
    );
    // 그래프는 상대 경로만 따라간다 → `@/` alias·패키지 import 가 있으면 그 너머를 못 본다. 0건이어야 한다.
    const nonRelative = graph.flatMap((file) =>
      [...readFileSync(file, "utf-8").matchAll(ANY_IMPORT)]
        .map((match) => match[1] ?? match[2] ?? match[3])
        .filter((specifier) => !specifier.startsWith("./") && !specifier.startsWith("../"))
        .map((specifier) => `${path.relative(PWA_DIR, file)} → ${specifier}`)
    );
    expect(nonRelative, "sw 그래프 안 비상대 import").toEqual([]);
    const nodeGlobal = new RegExp("\\b" + "pro" + "cess" + "\\b");
    expect(graph.filter((file) => nodeGlobal.test(readFileSync(file, "utf-8")))).toEqual([]);
  });

  it("SW 등록 호출부는 정확히 1곳 (service-worker-registrar.tsx)", () => {
    const files = filesContaining(listSourceFiles(SRC_ROOT), "serviceWorker" + ".register(");
    expect(files.map((file) => path.relative(SRC_ROOT, file))).toEqual([
      path.join("components", "layout", "service-worker-registrar.tsx"),
    ]);
  });
});
