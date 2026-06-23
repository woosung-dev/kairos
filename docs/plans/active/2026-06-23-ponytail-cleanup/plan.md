# Ponytail Cleanup Plan

## Goal

`ponytail-audit`에서 확인한 미사용 의존성, thin wrapper, 오래된 산출물을 줄여 런타임 설치 크기와 탐색 노이즈를 낮춘다.

## Scope

- 미사용 frontend/backend dependency 제거 또는 dev dependency 이동.
- 미사용 FE wrapper/helper/UI 파일 삭제.
- git에 추적된 디버그 PNG와 오래된 audit/sprint 산출물 정리.
- canonical doc에 이번 cleanup 기준을 기록한다.

## Verification

- Frontend typecheck.
- Backend pytest 중 의존성·DI 변경에 가까운 smoke subset.
- Git diff에서 제품 랜딩 스크린샷 3개는 유지 확인.
