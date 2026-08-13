// query-keys 레지스트리 형태 회귀 가드 — 키 배열 구조가 바뀌면 캐시/invalidate 가 깨진다
import { describe, expect, it } from "vitest";
import {
  actionKeys,
  auditKeys,
  externalDocumentKeys,
  inboxKeys,
  inviteKeys,
  meetingKeys,
  memberKeys,
  memoryKeys,
  noteKeys,
  onboardingKeys,
  projectKeys,
  ragKeys,
  workspaceKeys,
} from "../query-keys";

const WID = "wid-1";
const ID = "id-1";

describe("query-keys 형태 스냅샷", () => {
  it("workspaceKeys", () => {
    expect(workspaceKeys.all).toEqual(["workspaces"]);
    expect(workspaceKeys.list()).toEqual(["workspaces", "list"]);
    expect(workspaceKeys.detail(ID)).toEqual(["workspaces", "detail", ID]);
  });

  it("inboxKeys — params 없으면 {} sentinel, byWorkspace 는 invalidate prefix", () => {
    expect(inboxKeys.all).toEqual(["inbox"]);
    expect(inboxKeys.byWorkspace(WID)).toEqual(["inbox", "list", WID]);
    expect(inboxKeys.list(WID)).toEqual(["inbox", "list", WID, {}]);
    expect(inboxKeys.list(WID, { isProcessed: false })).toEqual([
      "inbox",
      "list",
      WID,
      { isProcessed: false },
    ]);
  });

  it("noteKeys — projectId 없으면 'all'", () => {
    expect(noteKeys.list(WID)).toEqual(["notes", "list", WID, "all"]);
    expect(noteKeys.list(WID, "p1")).toEqual(["notes", "list", WID, "p1"]);
    expect(noteKeys.detail(WID, ID)).toEqual(["notes", "detail", WID, ID]);
  });

  it("meetingKeys", () => {
    expect(meetingKeys.list(WID)).toEqual(["meetings", "list", WID, "all"]);
    expect(meetingKeys.list(WID, "p1")).toEqual(["meetings", "list", WID, "p1"]);
    expect(meetingKeys.detail(WID, ID)).toEqual(["meetings", "detail", WID, ID]);
    expect(meetingKeys.status(WID, ID)).toEqual(["meetings", "status", WID, ID]);
  });

  it("actionKeys", () => {
    expect(actionKeys.list(WID)).toEqual(["actions", "list", WID]);
  });

  it("projectKeys — params 유무로 list 형태 분기 (S28b RQ-KEY-COLLISION)", () => {
    expect(projectKeys.list(WID)).toEqual(["projects", "list", WID]);
    expect(projectKeys.list(WID, { status: "active" })).toEqual([
      "projects",
      "list",
      WID,
      { status: "active" },
    ]);
    expect(projectKeys.detail(WID, ID)).toEqual(["projects", "detail", WID, ID]);
    expect(projectKeys.members(WID, ID)).toEqual(["projects", "members", WID, ID]);
  });

  it("memberKeys / inviteKeys", () => {
    expect(memberKeys.list(WID)).toEqual(["members", "list", WID]);
    expect(inviteKeys.list(WID)).toEqual(["invites", "list", WID]);
    expect(inviteKeys.info("code-1")).toEqual(["invites", "info", "code-1"]);
  });

  it("memoryKeys", () => {
    expect(memoryKeys.detail(WID, ID)).toEqual(["memory", "detail", WID, ID]);
    expect(memoryKeys.recall(WID, "q")).toEqual(["memory", "recall", WID, "q"]);
  });

  it("ragKeys / auditKeys / onboardingKeys", () => {
    expect(ragKeys.all).toEqual(["rag"]);
    expect(auditKeys.promotions(WID, null)).toEqual([
      "audit",
      "promotions",
      WID,
      "all",
    ]);
    expect(auditKeys.promotions(WID, "note")).toEqual([
      "audit",
      "promotions",
      WID,
      "note",
    ]);
    expect(onboardingKeys.status(WID)).toEqual(["onboarding", "status", WID]);
    expect(onboardingKeys.status(null)).toEqual(["onboarding", "status", null]);
  });

  it("externalDocumentKeys", () => {
    expect(externalDocumentKeys.all).toEqual(["external-documents"]);
    expect(externalDocumentKeys.detail(WID, ID)).toEqual([
      "external-documents",
      "detail",
      WID,
      ID,
    ]);
  });
});
