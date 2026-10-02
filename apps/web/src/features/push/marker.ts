// 푸시 소유자 표식 — `localStorage["kairos:push:v1"] = { userId, subscriptionId }` (docs/requirements/pwa.md §5.5)
//
// ★브라우저 알림 권한은 origin 단위라 사용자를 구분하지 못한다. 이 표식이 "이 기기의 구독을 누가
//   켰는가" 의 유일한 근거다. userId 는 `useMe()` 의 내부 users.id (auth_user.id 아님).
// ★파싱 실패 = 없음. 키에 버전(v1)을 박아 두어 모양이 바뀌면 새 키로 옮긴다 (vercel client-localstorage-schema).
// ★localStorage 는 사파리 비공개 모드 등에서 throw 할 수 있다 → 모든 접근을 감싼다.
import { z } from "zod/v4";

export const PUSH_OWNER_MARKER_KEY = "kairos:push:v1";

export const pushOwnerMarkerSchema = z.object({
  userId: z.uuid(),
  subscriptionId: z.uuid(),
});

export type PushOwnerMarker = z.infer<typeof pushOwnerMarkerSchema>;

export type MarkerStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export function getBrowserMarkerStorage(): MarkerStorage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function readOwnerMarker(storage: MarkerStorage | null): PushOwnerMarker | null {
  if (!storage) return null;
  try {
    const raw = storage.getItem(PUSH_OWNER_MARKER_KEY);
    if (raw === null) return null;
    const parsed = pushOwnerMarkerSchema.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
}

export function writeOwnerMarker(storage: MarkerStorage | null, marker: PushOwnerMarker): void {
  if (!storage) return;
  try {
    storage.setItem(PUSH_OWNER_MARKER_KEY, JSON.stringify(marker));
  } catch {
    // 저장 실패 = 표식 없음. 다음 앱 로드 동기화가 이 기기 구독을 끊는다 (fail-closed).
  }
}

/**
 * compare-and-delete — 흐름 시작 때 읽은 subscriptionId 와 지금 값이 같을 때만 지운다.
 * 그 사이 다른 탭·켜기 흐름이 새 표식을 썼으면 남긴다.
 */
export function deleteOwnerMarkerIfMatches(
  storage: MarkerStorage | null,
  subscriptionId: string,
): void {
  if (!storage) return;
  if (readOwnerMarker(storage)?.subscriptionId !== subscriptionId) return;
  try {
    storage.removeItem(PUSH_OWNER_MARKER_KEY);
  } catch {
    // 지우지 못하면 다음 앱 로드 동기화가 다시 판정한다.
  }
}
