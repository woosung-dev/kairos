// Sprint 23 D4 — ItemPromoteModal 5 도메인 endpoint dispatch 검증
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ItemPromoteModal } from "../ItemPromoteModal";
import type { PromotableItemType } from "../ItemPromoteModal";

/* ── 픽스처 ── */
const SOURCE_WID = "11111111-1111-1111-1111-111111111111";
const TARGET_WID = "22222222-2222-2222-2222-222222222222";
const ITEM_ID = "33333333-3333-3333-3333-333333333333";

/* ── Clerk getToken 목 ── */
vi.mock("@clerk/nextjs", () => ({
  useAuth: () => ({
    getToken: vi.fn().mockResolvedValue("test-jwt"),
  }),
}));

/* ── sonner toast 목 (사이드 이펙트 격리) ── */
vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

/* ── workspaces hook 목 — target 1건만 반환 (selectedTarget default 채움) ── */
vi.mock("@/features/workspaces/hooks", () => ({
  useWorkspaces: () => ({
    data: [
      { id: SOURCE_WID, name: "personal-ws", type: "personal" },
      { id: TARGET_WID, name: "team-ws", type: "team" },
    ],
  }),
}));

/* ── itemType → 기대 endpoint segment + response newItemId 키 매트릭스 ──
 * BE 라우터 prefix 검증 결과 그대로. action 만 prefix 가 'action-items' (주의).
 */
const CASES: Array<{
  itemType: PromotableItemType;
  segment: string;
  newIdKey: string;
}> = [
  { itemType: "memory", segment: "memory", newIdKey: "new_memory_id" },
  { itemType: "meeting", segment: "meetings", newIdKey: "new_meeting_id" },
  { itemType: "note", segment: "notes", newIdKey: "new_note_id" },
  { itemType: "inbox", segment: "inbox", newIdKey: "new_inbox_id" },
  { itemType: "action", segment: "action-items", newIdKey: "new_action_id" },
];

/* ── 헬퍼: QueryClient wrapping ── */
function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

/* ── 픽스처 ── */
function makeOkResponse(newIdKey: string) {
  return {
    [newIdKey]: "99999999-9999-9999-9999-999999999999",
    audit_id: "88888888-8888-8888-8888-888888888888",
    status: "completed",
  };
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("ItemPromoteModal — 5 도메인 endpoint dispatch", () => {
  CASES.forEach(({ itemType, segment, newIdKey }) => {
    it(`itemType="${itemType}" → POST /workspaces/{src}/${segment}/{id}/promote with targetWorkspaceId body`, async () => {
      const onSuccess = vi.fn();
      const onOpenChange = vi.fn();

      const fetchMock = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => makeOkResponse(newIdKey),
      });
      vi.stubGlobal("fetch", fetchMock);

      renderWithClient(
        <ItemPromoteModal
          itemType={itemType}
          itemId={ITEM_ID}
          sourceWorkspaceId={SOURCE_WID}
          open={true}
          onOpenChange={onOpenChange}
          onSuccess={onSuccess}
        />,
      );

      // 확인 버튼 클릭 (mock workspaces 첫 team option 자동 선택됨)
      const confirmBtn = screen.getByRole("button", { name: /팀으로 올리기/ });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledTimes(1);
      });

      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];

      // URL 검증
      expect(url).toContain(
        `/api/v1/workspaces/${SOURCE_WID}/${segment}/${ITEM_ID}/promote`,
      );

      // method + headers + body 검증
      expect(init.method).toBe("POST");
      const headers = init.headers as Record<string, string>;
      expect(headers["Content-Type"]).toBe("application/json");
      expect(headers["Authorization"]).toBe("Bearer test-jwt");

      const body = JSON.parse(init.body as string);
      expect(body).toEqual({ targetWorkspaceId: TARGET_WID });

      // success callback 검증
      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledWith(
          "99999999-9999-9999-9999-999999999999",
          "88888888-8888-8888-8888-888888888888",
        );
      });

      // 모달 닫힘 검증
      expect(onOpenChange).toHaveBeenCalledWith(false);
    });
  });
});
