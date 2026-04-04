"use client";

import { Settings, Users, Link2, Building2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MemberList } from "@/features/members/components/member-list";
import { InviteManager } from "@/features/members/components/invite-manager";
import { useWorkspaceStore } from "@/features/workspaces/store";
import {
  useWorkspace,
  useUpdateWorkspaceSettings,
} from "@/features/workspaces/hooks";

const THRESHOLD_PRESETS = [0.7, 0.8, 0.9, 0.95] as const;

export default function SettingsPage() {
  const { activeWorkspaceId, workspaceRole, hasRole } = useWorkspaceStore();
  const { data: workspace } = useWorkspace(activeWorkspaceId ?? undefined);
  const updateSettings = useUpdateWorkspaceSettings(
    activeWorkspaceId ?? undefined
  );

  const isOwner = hasRole("owner");
  const currentThreshold = workspace?.inboxThreshold ?? 0.9;

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
      {/* 페이지 헤더 */}
      <div className="flex items-center gap-3 mb-6">
        <Settings className="w-5 h-5" style={{ color: "var(--text-secondary)" }} />
        <h1
          className="text-lg font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          설정
        </h1>
      </div>

      {/* 탭 구조 */}
      <Tabs defaultValue="members">
        <TabsList
          className="w-full justify-start gap-1 rounded-lg p-1 mb-6"
          style={{ background: "var(--surface)" }}
        >
          <TabsTrigger
            value="members"
            className="gap-1.5 cursor-pointer text-sm"
          >
            <Users className="w-4 h-4" />
            멤버
          </TabsTrigger>
          <TabsTrigger
            value="invites"
            className="gap-1.5 cursor-pointer text-sm"
          >
            <Link2 className="w-4 h-4" />
            초대
          </TabsTrigger>
          <TabsTrigger
            value="general"
            className="gap-1.5 cursor-pointer text-sm"
          >
            <Building2 className="w-4 h-4" />
            일반
          </TabsTrigger>
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

        {/* 초대 탭 */}
        <TabsContent value="invites">
          <div className="space-y-4">
            <h2
              className="text-sm font-medium"
              style={{ color: "var(--text-primary)" }}
            >
              초대 링크
            </h2>
            <InviteManager
              workspaceId={activeWorkspaceId}
              currentUserRole={workspaceRole}
            />
          </div>
        </TabsContent>

        {/* 일반 탭 */}
        <TabsContent value="general">
          <div className="space-y-6">
            {/* AI 자동 확정 임계값 */}
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
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
