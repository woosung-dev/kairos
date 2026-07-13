import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    // PR-3 c9: feature 경계 가드 — feature 내부에서 다른 feature 의 컴포넌트를
    // deep import 하면 결합이 생긴다. 공용이 필요하면 components/shared 로 승격.
    // (feature 내부는 상대 경로 import 컨벤션이라 자기 컴포넌트는 영향 없음.
    //  app/ 라우트가 feature 컴포넌트를 조립하는 것은 허용 — files 스코프 밖.)
    files: ["src/features/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/features/*/components/*"],
              message:
                "cross-feature 컴포넌트 deep import 금지 — 공용화가 필요하면 components/shared 로 승격하세요.",
            },
          ],
        },
      ],
    },
  },
]);

export default eslintConfig;
