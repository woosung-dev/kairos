# agy-fix-regression — Sprint 27d 결함 4건 회귀 검증

| BUG ID | 회귀 가드 내용 | 결과 | 검증 증거 및 테스트 스펙 |
| :--- | :--- | :--- | :--- |
| **BUG-S27d-1** | /dashboard + ⌘K 진입 시 console.error 0건 검증 (PopoverTrigger nativeButton 회귀) | **PASS** | `home.spec.ts`, `onboarding-tooltip-first-visit.spec.ts` 테스트 통과 및 console.error 0건 확인 |
| **BUG-S27d-2** | `/actions` 직접 진입 시 `/inbox`로 정상 리다이렉트 및 404 차단 | **PASS** | `actions-redirect.spec.ts` E2E 테스트 통과 |
| **BUG-S27d-3** | `evil.exe` 파일 `text/plain` MIME 타입으로 위장 업로드 시 415 차단 | **PASS** | `test_upload_validation.py` 백엔드 유닛 테스트 20개 전원 통과 |
| **BUG-S27d-4** | FE(Next.js) 및 BE(FastAPI) 보안 헤더 주입 여부 검증 | **PASS** | curl 헤더 직접 검증 완료 (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy` 등 확보) |
