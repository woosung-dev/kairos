// 워크스페이스 타입 추론 — BE 응답 type 누락 (legacy row) 시 name 패턴 fallback
import type { Workspace } from "./types";

const PERSONAL_SEED_SUFFIX = "의 개인 Kairos";

/**
 * BE 응답 우선 사용. 누락 시 Sprint 15 lazy seed 패턴 `{display_name}의 개인 Kairos` 휴리스틱.
 */
export function inferWorkspaceType(
  workspace: Pick<Workspace, "name" | "type">,
): "personal" | "team" {
  if (workspace.type === "personal" || workspace.type === "team") {
    return workspace.type;
  }
  if (workspace.name?.endsWith(PERSONAL_SEED_SUFFIX)) {
    return "personal";
  }
  return "team";
}
