# Changelog

All notable changes to Kairos are documented here.

---

## [0.1.0.1] - 2026-05-12

### Added
- E2E Playwright 골든패스 2개: 인증 리다이렉트 테스트(`auth.spec.ts`) + 미팅 업로드→STT→요약 완료 흐름 테스트(`meeting-upload.spec.ts`)
- 한국어 TTS 오디오 fixture (`test.m4a`, 78KB) — Playwright 파일 업로드 E2E 테스트용
- `.github/workflows/test.yml` E2E 잡 활성화 방법 가이드 주석 추가

### Fixed
- `useMeetingDetail` 훅 폴링 로직 개선: 네트워크 오류 발생 시 폴링이 영구 중단되던 버그 수정 — 이제 완료/실패 상태에서만 폴링을 중단함

### Changed
- 미팅 상세 페이지(`meeting-detail.tsx`)가 STT 처리 중 상태 배지를 자동으로 업데이트하도록 개선 — `refetchInterval` 추가

---

## [0.1.0] - 2026-05-12

Initial baseline: Sprint 1~11 PR1 완료 상태 기준
