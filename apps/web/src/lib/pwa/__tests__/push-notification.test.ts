// T-PWA-45 (알림 이동 대상 정제) · T-PWA-46 (SW push) · T-PWA-47 (SW notificationclick)
// (docs/plans/active/2026-10-02-pwa/test-matrix.md, docs/requirements/pwa.md §5.4 · §5.5)
import { describe, expect, it, vi } from "vitest";
import {
  FALLBACK_NOTIFICATION_TARGET,
  NOTIFICATION_ICON,
  handlePush,
  openNotificationTarget,
  resolveNotificationTarget,
  type ClientsLike,
  type KairosNotificationOptions,
  type WindowClientLike,
} from "../push-notification";

const ORIGIN = "https://kairos.woosung.dev";
const MEETING_ID = "3f2c8a10-1b2c-4d5e-8f90-a1b2c3d4e5f6";
const WORKSPACE_ID = "9a1e7b20-3c4d-4e5f-9a0b-c1d2e3f4a5b6";

function pushData(value: unknown) {
  return { json: () => value };
}

function brokenJson() {
  return {
    json: () => {
      throw new SyntaxError("Unexpected token");
    },
  };
}

async function runPush(data: Parameters<typeof handlePush>[0]) {
  const showNotification = vi.fn<(title: string, options: KairosNotificationOptions) => Promise<void>>(
    () => Promise.resolve()
  );
  await handlePush(data, showNotification);
  return showNotification;
}

describe("T-PWA-45 resolveNotificationTarget — 알림 이동 대상 정제", () => {
  it("/meetings/<uuid> · /dashboard 는 통과한다", () => {
    expect(resolveNotificationTarget(`/meetings/${MEETING_ID}`, ORIGIN)).toBe(
      `/meetings/${MEETING_ID}`
    );
    expect(resolveNotificationTarget("/dashboard", ORIGIN)).toBe("/dashboard");
    expect(resolveNotificationTarget(`${ORIGIN}/meetings/${MEETING_ID}`, ORIGIN)).toBe(
      `/meetings/${MEETING_ID}`
    );
  });

  it("외부 origin · 스킴 · 모양이 다른 경로는 /dashboard 로 바꾼다", () => {
    for (const raw of [
      "//evil.com",
      "https://evil.com",
      "/\\evil.com",
      "javascript:alert(1)",
      "/meetings/x",
      `/meetings/${MEETING_ID}/edit`,
      "/settings",
      "",
    ]) {
      expect(resolveNotificationTarget(raw, ORIGIN), raw).toBe(FALLBACK_NOTIFICATION_TARGET);
    }
    expect(resolveNotificationTarget(undefined, ORIGIN)).toBe(FALLBACK_NOTIFICATION_TARGET);
    expect(resolveNotificationTarget(42, ORIGIN)).toBe(FALLBACK_NOTIFICATION_TARGET);
  });

  it("workspace 쿼리는 /meetings/<uuid> 의 workspace=<uuid> 1개만 남긴다", () => {
    expect(
      resolveNotificationTarget(`/meetings/${MEETING_ID}?workspace=${WORKSPACE_ID}`, ORIGIN)
    ).toBe(`/meetings/${MEETING_ID}?workspace=${WORKSPACE_ID}`);
    expect(resolveNotificationTarget(`/meetings/${MEETING_ID}?workspace=x`, ORIGIN)).toBe(
      `/meetings/${MEETING_ID}`
    );
    expect(
      resolveNotificationTarget(
        `/meetings/${MEETING_ID}?workspace=${WORKSPACE_ID}&next=//evil.com#h`,
        ORIGIN
      )
    ).toBe(`/meetings/${MEETING_ID}?workspace=${WORKSPACE_ID}`);
    expect(resolveNotificationTarget(`/dashboard?workspace=${WORKSPACE_ID}`, ORIGIN)).toBe(
      "/dashboard"
    );
  });
});

describe("T-PWA-46 push — showNotification 1회 · 문구는 kind 로 · 예외 0", () => {
  it.each([
    ["meeting.completed", "회의 처리 완료", "업로드한 회의의 요약·액션이 준비됐어요."],
    [
      "meeting.failed",
      "회의 처리 실패",
      "업로드한 회의를 처리하지 못했어요. 눌러서 확인하세요.",
    ],
  ])("유효 페이로드 %s → kind 문구 · tag · 딥링크 URL · icon", async (kind, title, body) => {
    const showNotification = await runPush(
      pushData({ v: 1, kind, meetingId: MEETING_ID, workspaceId: WORKSPACE_ID })
    );
    expect(showNotification).toHaveBeenCalledTimes(1);
    expect(showNotification).toHaveBeenCalledWith(title, {
      body,
      icon: NOTIFICATION_ICON,
      lang: "ko",
      tag: `meeting-${MEETING_ID}`,
      data: { url: `/meetings/${MEETING_ID}?workspace=${WORKSPACE_ID}` },
    });
  });

  it("workspaceId 가 비UUID·누락이면 쿼리 없는 상세 URL (알림은 그대로)", async () => {
    for (const workspaceId of ["not-a-uuid", undefined, 7]) {
      const showNotification = await runPush(
        pushData({ v: 1, kind: "meeting.completed", meetingId: MEETING_ID, workspaceId })
      );
      expect(showNotification).toHaveBeenCalledTimes(1);
      const [title, options] = showNotification.mock.calls[0];
      expect(title).toBe("회의 처리 완료");
      expect(options.data.url).toBe(`/meetings/${MEETING_ID}`);
      expect(options.tag).toBe(`meeting-${MEETING_ID}`);
    }
  });

  it("알 수 없는 kind · JSON 파싱 실패 · meetingId 비UUID · v 불일치 · 본문 없음 → 일반 알림 + /dashboard", async () => {
    const cases = [
      pushData({ v: 1, kind: "note.created", meetingId: MEETING_ID }),
      brokenJson(),
      pushData({ v: 1, kind: "meeting.completed", meetingId: "../../evil" }),
      pushData({ v: 2, kind: "meeting.completed", meetingId: MEETING_ID }),
      pushData("meeting.completed"),
      null,
    ];
    for (const data of cases) {
      const showNotification = await runPush(data);
      expect(showNotification).toHaveBeenCalledTimes(1);
      expect(showNotification).toHaveBeenCalledWith("Kairos", {
        body: "새 알림이 있어요.",
        icon: NOTIFICATION_ICON,
        lang: "ko",
        data: { url: "/dashboard" },
      });
    }
  });

  it("서버가 보낸 문자열을 URL·문구로 쓰지 않는다 (추가 필드 무시)", async () => {
    const showNotification = await runPush(
      pushData({
        v: 1,
        kind: "meeting.completed",
        meetingId: MEETING_ID,
        workspaceId: WORKSPACE_ID,
        title: "극비 회의",
        url: "https://evil.com",
      })
    );
    const [title, options] = showNotification.mock.calls[0];
    expect(JSON.stringify([title, options])).not.toMatch(/극비|evil/);
  });
});

interface FakeWindow extends WindowClientLike {
  readonly focus: ReturnType<typeof vi.fn<() => Promise<unknown>>>;
  readonly navigate: ReturnType<typeof vi.fn<(url: string) => Promise<unknown>>>;
}

function fakeWindow(url: string, navigate?: (url: string) => Promise<unknown>): FakeWindow {
  return {
    url,
    focus: vi.fn(() => Promise.resolve(undefined)),
    navigate: vi.fn(navigate ?? (() => Promise.resolve(undefined))),
  };
}

function fakeClients(windows: readonly WindowClientLike[]) {
  const openWindow = vi.fn<(url: string) => Promise<null>>(() => Promise.resolve(null));
  const matchAll = vi.fn(() => Promise.resolve(windows));
  const clients: ClientsLike = { matchAll, openWindow };
  return { clients, openWindow, matchAll };
}

describe("T-PWA-47 notificationclick — 같은 origin 창 재사용 · 정제된 대상만", () => {
  const meetingTarget = `${ORIGIN}/meetings/${MEETING_ID}`;

  it("같은 origin 창이 있으면 focus + navigate(target), 새 창 0", async () => {
    const window = fakeWindow(`${ORIGIN}/dashboard`);
    const { clients, openWindow, matchAll } = fakeClients([window]);
    await openNotificationTarget({ url: `/meetings/${MEETING_ID}` }, ORIGIN, clients);
    expect(matchAll).toHaveBeenCalledWith({ type: "window", includeUncontrolled: true });
    expect(window.focus).toHaveBeenCalledTimes(1);
    expect(window.navigate).toHaveBeenCalledWith(meetingTarget);
    expect(openWindow).not.toHaveBeenCalled();
  });

  it("navigate 가 reject 하면 openWindow(target)", async () => {
    const window = fakeWindow(`${ORIGIN}/dashboard`, () =>
      Promise.reject(new TypeError("not controlled"))
    );
    const { clients, openWindow } = fakeClients([window]);
    await openNotificationTarget({ url: `/meetings/${MEETING_ID}` }, ORIGIN, clients);
    expect(openWindow).toHaveBeenCalledWith(meetingTarget);
  });

  it("창이 없거나 다른 origin 창뿐이면 openWindow(target)", async () => {
    for (const windows of [[], [fakeWindow("https://evil.com/")]]) {
      const { clients, openWindow } = fakeClients(windows);
      await openNotificationTarget({ url: `/meetings/${MEETING_ID}` }, ORIGIN, clients);
      expect(openWindow).toHaveBeenCalledWith(meetingTarget);
    }
  });

  it("조작된 data.url · data 없음 → /dashboard", async () => {
    for (const data of [{ url: "https://evil.com/phish" }, { url: "//evil.com" }, null, "x"]) {
      const { clients, openWindow } = fakeClients([]);
      await openNotificationTarget(data, ORIGIN, clients);
      expect(openWindow).toHaveBeenCalledWith(`${ORIGIN}/dashboard`);
    }
  });

  it("workspace 쿼리는 유지하고 덧붙인 다른 쿼리·hash 는 버린다", async () => {
    const window = fakeWindow(`${ORIGIN}/dashboard`);
    const { clients } = fakeClients([window]);
    await openNotificationTarget(
      { url: `/meetings/${MEETING_ID}?workspace=${WORKSPACE_ID}&next=//evil.com#h` },
      ORIGIN,
      clients
    );
    expect(window.navigate).toHaveBeenCalledWith(`${meetingTarget}?workspace=${WORKSPACE_ID}`);
  });
});
