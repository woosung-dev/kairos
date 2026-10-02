// 웹 푸시 BE API 호출 (docs/requirements/pwa.md §5.2 — API-001~003, 사용자 단위 `/users/me/*`)
import type { ApiClient } from "@/lib/api-client";
import type { components } from "@/types/api.gen";

// I-22 — wire 타입은 계약 생성물에서 가져온다. 수기 interface 를 새로 쓰지 않는다.
type Schemas = components["schemas"];

export type PushConfig = Schemas["PushConfigResponse"];
export type PushSubscriptionUpsertBody = Schemas["PushSubscriptionUpsertRequest"];
export type PushSubscriptionUpsertResult = Schemas["PushSubscriptionUpsertResponse"];

/** API-001 — VAPID 설정이 다 있을 때만 `isEnabled=true` (아니면 설정 탭을 숨긴다). */
export async function fetchPushConfig(api: ApiClient): Promise<PushConfig> {
  return api.fetch<PushConfig>("/users/me/push-config");
}

/** API-002 — endpoint 단위 upsert. 같은 endpoint 면 id 가 유지되고 현재 사용자로 rebind 된다. */
export async function upsertPushSubscription(
  api: ApiClient,
  body: PushSubscriptionUpsertBody,
): Promise<PushSubscriptionUpsertResult> {
  return api.fetch<PushSubscriptionUpsertResult>("/users/me/push-subscriptions", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

/**
 * API-003 — id 로 지정한다 (endpoint 는 capability URL 이라 경로·접근 로그에 넣지 않는다).
 * 없거나 남의 것이어도 204 다.
 */
export async function deletePushSubscription(
  api: ApiClient,
  subscriptionId: string,
): Promise<void> {
  await api.fetch<void>(
    `/users/me/push-subscriptions/${encodeURIComponent(subscriptionId)}`,
    { method: "DELETE" },
  );
}
