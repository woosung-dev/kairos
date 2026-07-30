"use client";

// Sprint 23 D2 Variant C — 워크스페이스 설정 페이지 (Compact Header + Geist Mono + ?tab=*)

import { Suspense } from "react";
import { Settings, Users, Link2, Building2, PlugZap, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MemberList } from "@/features/members/components/member-list";
import { InviteManager } from "@/features/members/components/invite-manager";
import { useMembers, useInvites } from "@/features/members/hooks";
import { AuditList } from "@/features/audit/components/audit-list";
import { useWorkspaceStore } from "@/features/workspaces/store";
import {
  useWorkspace,
  useUpdateWorkspaceSettings,
} from "@/features/workspaces/hooks";
import { DangerZone } from "@/features/workspaces/components/DangerZone";
import { GoogleDrivePrototype } from "@/features/workspaces/components/google-drive-prototype";
import { inferWorkspaceType } from "@/features/workspaces/utils";

const THRESHOLD_PRESETS = [0.7, 0.8, 0.9, 0.95] as const;
// Sprint 24 Wave 2 T-AUDIT-VIEW: audit tab 추가 — admin/owner 만 노출.
const VALID_TABS = ["members", "invites", "general", "audit", "integrations"] as const;
const IS_GOOGLE_DRIVE_PROTOTYPE_ENABLED = process.env.NODE_ENV !== "production";

const ROLE_LABEL: Record<string, string> = {
  owner: "owner",
  admin: "admin",
  member: "member",
  viewer: "viewer",
};

const MONO_STYLE = {
  fontFamily: "var(--font-mono)",
  fontVariantNumeric: "tabular-nums" as const,
};

// Sprint 23 Codex 2.5차 P1 fix: useSearchParams() 가 Next.js production build 에서 Suspense
// boundary 필요. SettingsContent 로 분리 + Suspense wrap → `next build` Missing Suspense 회피.
export default function SettingsPage() {
  return (
    <Suspense
      fallback={
        <div
          className="flex items-center justify-center h-full"
          style={{ color: "var(--text-muted)" }}
        >
          불러오는 중...
        </div>
      }
    >
      <SettingsContent />
    </Suspense>
  );
}

function SettingsContent() {
  const { activeWorkspaceId, workspaceRole, hasRole } = useWorkspaceStore();
  const { data: workspace } = useWorkspace(activeWorkspaceId ?? undefined);
  const updateSettings = useUpdateWorkspaceSettings(
    activeWorkspaceId ?? undefined,
  );
  const { data: members } = useMembers(activeWorkspaceId ?? undefined);
  // Sprint 23 Codex 7차 P2 fix: useInvites 는 admin/owner 만 호출 (BE 가 admin+ 강제 → 403 회피).
  // member/viewer 에게는 enabled=false 로 차단. tab count badge 는 0 또는 미표시.
  const isAdminOrOwner = hasRole("admin");
  const { data: invites } = useInvites(activeWorkspaceId ?? undefined, {
    enabled: isAdminOrOwner,
  });
  const router = useRouter();
  const searchParams = useSearchParams();

  // 로딩 중 0 으로 깜빡이지 않도록 데이터 도착 전에는 대시 표시
  const memberCount = members?.length;
  const activeInviteCount = invites?.filter(
    (invite) => invite.isActive,
  ).length;
  const isOwner = hasRole("owner");
  const currentThreshold = workspace?.inboxThreshold ?? 0.9;

  const tabParam = searchParams.get("tab");
  const activeTab = (VALID_TABS as readonly string[]).includes(tabParam ?? "") &&
    (tabParam !== "integrations" || (isOwner && IS_GOOGLE_DRIVE_PROTOTYPE_ENABLED))
    ? tabParam ?? "members"
    : "members";

  const handleTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", value);
    router.replace(`/settings?${params.toString()}`, { scroll: false });
  };

  if (!activeWorkspaceId) {
    return (
      <div
        className="flex items-center justify-center h-full"
        style={{ color: "var(--text-muted)" }}
      >
        워크스페이스를 선택해주세요
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      {/* Compact 헤더 — Satoshi 32px h1 + Geist Mono 11px subtitle */}
      <header className="mb-8">
        <h1
          className="flex items-center gap-2.5 tracking-tight"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 32,
            fontWeight: 700,
            lineHeight: 1.1,
            color: "var(--text-primary)",
          }}
        >
          <Settings className="w-7 h-7" aria-hidden />
          설정
        </h1>
        <p
          className="mt-2 truncate"
          style={{
            ...MONO_STYLE,
            fontSize: 11,
            color: "var(--text-muted)",
          }}
        >
          {workspace?.name ?? "—"} ·{" "}
          {workspaceRole ? ROLE_LABEL[workspaceRole] : "—"} · 멤버{" "}
          {memberCount ?? "—"}
        </p>
      </header>

      {/* 탭 구조 — ?tab=* deep-link 동기화 + count badge */}
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList
          className="w-full justify-start gap-1 rounded-lg p-1 mb-6"
          style={{ background: "var(--surface)" }}
        >
          <TabsTrigger
            value="members"
            className="gap-1.5 cursor-pointer text-sm"
          >
            <Users className="w-4 h-4" aria-hidden />
            멤버
            <span
              aria-label={`멤버 수 ${memberCount ?? "로딩 중"}`}
              style={{
                ...MONO_STYLE,
                fontSize: 11,
                color: "var(--text-muted)",
                marginLeft: 2,
              }}
            >
              {memberCount ?? "—"}
            </span>
          </TabsTrigger>
          <TabsTrigger
            value="invites"
            className="gap-1.5 cursor-pointer text-sm"
          >
            <Link2 className="w-4 h-4" aria-hidden />
            초대
            <span
              aria-label={`활성 초대 ${activeInviteCount ?? "로딩 중"}`}
              style={{
                ...MONO_STYLE,
                fontSize: 11,
                color: "var(--text-muted)",
                marginLeft: 2,
              }}
            >
              {activeInviteCount ?? "—"}
            </span>
          </TabsTrigger>
          <TabsTrigger
            value="general"
            className="gap-1.5 cursor-pointer text-sm"
          >
            <Building2 className="w-4 h-4" aria-hidden />
            일반
          </TabsTrigger>
          {isOwner && IS_GOOGLE_DRIVE_PROTOTYPE_ENABLED && (
            <TabsTrigger
              value="integrations"
              className="gap-1.5 cursor-pointer text-sm"
            >
              <PlugZap className="w-4 h-4" aria-hidden />
              연동
              <span
                style={{
                  ...MONO_STYLE,
                  fontSize: 10,
                  color: "var(--accent)",
                  marginLeft: 2,
                }}
              >
                P
              </span>
            </TabsTrigger>
          )}
          {/* Sprint 24 Wave 2 T-AUDIT-VIEW: Audit 탭 — admin/owner 만 노출.
              viewer/member 에게는 tab trigger 자체를 미렌더 → URL 직접 접근도 BE 403 fall-through. */}
          {isAdminOrOwner && (
            <TabsTrigger
              value="audit"
              data-testid="audit-tab-trigger"
              className="gap-1.5 cursor-pointer text-sm"
            >
              <ShieldCheck className="w-4 h-4" aria-hidden />
              Audit
            </TabsTrigger>
          )}
        </TabsList>

        {/* 멤버 탭 */}
        <TabsContent value="members">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2
                className="text-sm font-medium"
                style={{ color: "var(--text-primary)" }}
              >
                워크스페이스 멤버
              </h2>
            </div>
            <MemberList
              workspaceId={activeWorkspaceId}
              currentUserRole={workspaceRole}
            />
          </div>
        </TabsContent>

        {/* 초대 탭 — Sprint 23 Codex 9차 P2 fix: admin+ 만 InviteManager mount.
            member/viewer 가 ?tab=invites URL 직접 접근 시 InviteManager 가 useInvites 무조건
            호출 → 403. admin 분기로 mount 자체 차단. */}
        <TabsContent value="invites">
          <div className="space-y-4">
            <h2
              className="text-sm font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              초대 링크
            </h2>
            {isAdminOrOwner ? (
              <InviteManager
                workspaceId={activeWorkspaceId}
                currentUserRole={workspaceRole}
              />
            ) : (
              <p
                className="text-sm"
                style={{ color: "var(--text-muted)" }}
              >
                초대 링크 관리는 관리자(Admin) 이상 권한에서만 가능합니다.
              </p>
            )}
          </div>
        </TabsContent>

        {/* 일반 탭 */}
        <TabsContent value="general">
          <div className="space-y-6">
            {isOwner && (
              <div className="space-y-4">
                <h2
                  className="text-sm font-medium"
                  style={{ color: "var(--text-primary)" }}
                >
                  AI 자동 확정 임계값
                </h2>
                <p
                  className="text-sm leading-relaxed"
                  style={{ color: "var(--text-muted)" }}
                >
                  AI가 Inbox 항목을 자동으로 확정하는 신뢰도 기준입니다. 값이
                  높을수록 더 정확한 항목만 자동 확정됩니다.
                </p>

                <div className="flex gap-2">
                  {THRESHOLD_PRESETS.map((preset) => {
                    const isActive =
                      Math.abs(currentThreshold - preset) < 0.001;
                    return (
                      <button
                        key={preset}
                        type="button"
                        disabled={updateSettings.isPending}
                        onClick={() =>
                          updateSettings.mutate({ inbox_threshold: preset })
                        }
                        className="px-4 py-2 rounded-md text-sm font-medium cursor-pointer transition-colors duration-150"
                        style={{
                          ...MONO_STYLE,
                          background: isActive
                            ? "var(--accent)"
                            : "var(--surface-active)",
                          color: isActive
                            ? "var(--background)"
                            : "var(--text-primary)",
                          opacity: updateSettings.isPending ? 0.6 : 1,
                        }}
                      >
                        {Math.round(preset * 100)}%
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {!isOwner && (
              <div className="space-y-4">
                <h2
                  className="text-sm font-medium"
                  style={{ color: "var(--text-primary)" }}
                >
                  워크스페이스 정보
                </h2>
                <p
                  className="text-sm"
                  style={{ color: "var(--text-muted)" }}
                >
                  워크스페이스 설정 변경은 소유자만 가능합니다.
                </p>
              </div>
            )}

            {/* 위험 구역 — owner + team 워크스페이스만 (personal 은 BE 도 차단, I-19) */}
            {isOwner &&
              workspace &&
              inferWorkspaceType({
                name: workspace.name,
                type: workspace.type,
              }) === "team" && (
                <DangerZone
                  workspaceId={activeWorkspaceId}
                  workspaceName={workspace.name}
                />
              )}
          </div>
        </TabsContent>

        {/* Sprint 24 Wave 2 T-AUDIT-VIEW: Audit 탭 — admin/owner 만 mount.
            viewer/member 가 ?tab=audit URL 직접 접근 시 admin gate 가 mount 차단. */}
        <TabsContent value="audit">
          <div className="space-y-4">
            <h2
              className="text-sm font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              Promote Audit 로그
            </h2>
            <p
              className="text-sm leading-relaxed"
              style={{ color: "var(--text-muted)" }}
            >
              다른 워크스페이스에서 이 워크스페이스로 promote 된 회의·노트·Inbox·액션
              항목의 audit trail 입니다. 관리자(Admin) 이상 권한에서만 확인할 수
              있습니다.
            </p>
            {isAdminOrOwner ? (
              <AuditList workspaceId={activeWorkspaceId} />
            ) : (
              <p
                className="text-sm"
                style={{ color: "var(--text-muted)" }}
              >
                Audit 로그 조회는 관리자(Admin) 이상 권한에서만 가능합니다.
              </p>
            )}
          </div>
        </TabsContent>

        {isOwner && IS_GOOGLE_DRIVE_PROTOTYPE_ENABLED && (
          <TabsContent value="integrations">
            <GoogleDrivePrototype
              workspaceName={workspace?.name ?? "이 워크스페이스"}
              variant={searchParams.get("variant")}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
