# Sprint 27d Codex Final Audit Context Notes

## 확인된 사실

- 현재 브랜치: `sprint-27d/pre-ga-audit-prompts`.
- 최근 audit 관련 commit: `6d70eb2` opus 1차, `9082041` opus follow-up fix, `34f61b6` agy cross-check, `15fb24f` agy 산출물 이동.
- 입력 파일의 agy 경로는 `docs/sprints/sprint-27d-pre-ga-audit/agy/`로 되어 있으나 실제 파일은 `docs/sprints/sprint-27d-pre-ga-audit/` 루트에 존재한다.
- Opus composite: `7.53/10`, verdict `GO`.
- Agy composite: `8.32/10`, verdict `GO`.
- Agy는 BUG-S27d-1/2/3/4 회귀를 모두 `PASS`로 판정했고, DEFERRED E3/E5/E7도 `PASS`로 보강했다.

## 실행 결정

- production audit와 Sentry 검증은 사용자 정책에 따라 SKIP한다.
- 로컬 FE/BE가 응답하지 않으면 가능한 범위에서 테스트 명령과 정적/HTTP 검증으로 증거를 남기고, 서버 의존 검증은 명시적으로 기록한다.
- 신규 결함은 `BUG-S27d-CODEX-*` prefix로만 기록한다.

## 진행 중 확인

- Playwright MCP는 초기 세션 도구 목록에 없었고 `~/.codex/config.toml`에도 없었다.
- `@playwright/mcp` npm 최신 확인 버전: `0.0.75`.
- `codex mcp add playwright -- npx @playwright/mcp@latest` 로 전역 MCP 서버 등록 완료. 현재 세션 도구 목록은 시작 시점 고정이라 새 Playwright MCP 도구는 다음 Codex 세션부터 노출될 가능성이 높다.
- `uv run pytest tests/upload/test_upload_validation.py` 결과: 20 passed.
- FE 전체 병렬 E2E 최초 run: setup 통과, 7 passed / 1 skipped / 2 failed. 실패 2건은 focused 재실행에서 3 passed 로 통과해 product regression 이 아니라 test flake 로 분류했다.
- FE/BE security headers 4종은 실제 HTTP response 에서 확인했다.
- Fresh Clerk 로그인 후 API adversarial smoke 결과: SQLi-like query 200 empty, UUID/path/method tamper fail-closed, upload spoofing 415, concurrent evil upload 5회 모두 415.
