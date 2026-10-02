"use client";

// 웹 푸시 앱 로드 동기화 (docs/requirements/pwa.md §5.5) — `(app)` 셸에 1번 마운트한다. 아무것도 렌더하지 않는다.
// 표식 일치면 API-002 재전송, 불일치면 로컬 unsubscribe 만, 등록이 사라졌으면 API-003 정리.
import { usePushAppLoadSync } from "../hooks";

export function PushSync() {
  usePushAppLoadSync();
  return null;
}
