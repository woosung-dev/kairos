# Ponytail Cleanup Context Notes

## 2026-06-23

- `frontend/public/landing/screenshots/*.png`는 랜딩 `ProductShotsSection`에서 직접 참조하므로 삭제 대상에서 제외한다.
- shadcn 원본 수정 금지 원칙 때문에 `components/ui`는 수정하지 않고 미사용 `tooltip.tsx`만 삭제한다.
- `testcontainers`는 backend runtime import가 없고 tests/scripts에서만 쓰이므로 dev dependency가 맞다.
- `tenacity`는 직접 dependency에서 제거한다. 단 `google-genai` 전이 의존성이라 `uv.lock`에는 남는다.
- `clerk-backend-api`는 runtime import가 0건이다. 현재 Clerk JWT 검증은 PyJWT 기반 구현이다.
