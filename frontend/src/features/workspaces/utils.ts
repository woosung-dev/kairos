// 워크스페이스 타입 추론 + BL-035 동일 이름 disambiguation 유틸
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

/**
 * BL-035: 동일 이름 워크스페이스 disambiguation — created_at 오름차순 #1, #2... 접미사.
 * 단일 이름은 접미사 미부여. type (team/personal) 별로 그룹화 → 두 타입 간 번호 충돌 없음.
 *
 * 반환: Map<workspace.id, "#N">. 그룹 크기 1인 워크스페이스는 Map 미포함 (suffix 없음).
 */
export function buildDisambiguationMap(
  workspaces: Pick<Workspace, "id" | "name" | "type" | "createdAt">[],
): Map<string, string> {
  const suffixMap = new Map<string, string>();
  const groups = new Map<string, typeof workspaces>();
  workspaces.forEach((ws) => {
    const key = `${inferWorkspaceType(ws)}:${ws.name}`;
    const arr = groups.get(key);
    if (arr) arr.push(ws);
    else groups.set(key, [ws]);
  });
  groups.forEach((group) => {
    if (group.length < 2) return;
    const sorted = [...group].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
    sorted.forEach((ws, idx) => {
      suffixMap.set(ws.id, `#${idx + 1}`);
    });
  });
  return suffixMap;
}
