"use client";

// ADR-026 — Google Drive 팀 지식 연동 (owner 전용).
//
// Phase 0 UX 결론을 따른다: A(권한 우선 설명) + B(단계형 import). C(지식 현황)는
// 실제 데이터가 생긴 뒤 관리 표면으로 쓴다 — 그래서 문서 목록은 발행된 문서가
// 있을 때만 나타난다.

import { useState } from "react";
import {
  AlertTriangle,
  Database,
  FileText,
  Loader2,
  LockKeyhole,
  RefreshCw,
  SearchCheck,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useProjects } from "@/features/projects/hooks";
import { formatDateTime } from "@/lib/format-date";
import {
  useCreateGoogleDriveAuthorizationUrl,
  useDisconnectGoogleDrive,
  useGoogleDriveConnection,
  useGoogleDriveDocuments,
  useImportGoogleDriveDocuments,
  useIntegrationSyncRun,
  useResyncGoogleDriveDocument,
  useUnpublishGoogleDriveDocument,
} from "../hooks";
import { useGooglePicker } from "../use-google-picker";
import type { DocumentSyncStatus, ExternalDocument } from "../api";

const SYNC_STATUS_LABEL: Record<DocumentSyncStatus, string> = {
  pending: "대기 중",
  processing: "동기화 중",
  completed: "검색 가능",
  failed: "실패",
  stale: "동기화 필요",
  reauth_required: "재인증 필요",
  purged: "원본 소실 — 회수됨",
};

/** 사용자 조치가 필요한 상태만 강조한다. */
const ATTENTION_STATUSES: ReadonlySet<DocumentSyncStatus> = new Set([
  "failed",
  "stale",
  "reauth_required",
  "purged",
]);

interface GoogleDrivePanelProps {
  workspaceId: string;
}

export function GoogleDrivePanel({ workspaceId }: GoogleDrivePanelProps) {
  const [syncRunId, setSyncRunId] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string>("");

  const { data: connection, isPending: isConnectionPending } =
    useGoogleDriveConnection(workspaceId);
  const isConnected = !!connection && connection.status !== "disabled";

  const { data: documents } = useGoogleDriveDocuments(workspaceId, {
    enabled: isConnected,
  });
  const { data: projects } = useProjects(workspaceId);
  const { data: syncRun } = useIntegrationSyncRun(workspaceId, syncRunId);

  const picker = useGooglePicker();
  const authorize = useCreateGoogleDriveAuthorizationUrl(workspaceId);
  const importDocuments = useImportGoogleDriveDocuments(workspaceId);
  const resync = useResyncGoogleDriveDocument(workspaceId);
  const unpublish = useUnpublishGoogleDriveDocument(workspaceId);
  const disconnect = useDisconnectGoogleDrive(workspaceId);

  const handleConnect = () => {
    authorize.mutate(undefined, {
      // BE 가 발급한 인가 URL 로 전체 이동한다. state·PKCE 는 서버가 쥐고 있다.
      onSuccess: (url) => window.location.assign(url),
      onError: () => toast.error("Google 인가 URL 을 만들지 못했습니다"),
    });
  };

  const handlePickAndImport = async () => {
    const picked = await picker.open();
    if (picked.length === 0) return;

    importDocuments.mutate(
      { fileIds: picked.map((file) => file.id), projectId: projectId || null },
      {
        onSuccess: (createdSyncRunId) => {
          setSyncRunId(createdSyncRunId);
          toast.success(`${picked.length}개 문서를 가져오는 중입니다`);
        },
        onError: () => toast.error("가져오기를 시작하지 못했습니다"),
      },
    );
  };

  const handleDisconnect = () => {
    disconnect.mutate(undefined, {
      onSuccess: (result) => {
        if (result.revoked) {
          toast.success(
            `연결을 해제하고 문서 ${result.unpublishedDocuments}건을 회수했습니다`,
          );
          return;
        }
        // 해제 실패가 아니다 — Kairos 쪽 회수는 끝났고 Google 폐기만 미확인이다.
        toast.warning(
          `문서 ${result.unpublishedDocuments}건을 회수했습니다. ` +
            "Google 계정의 권한은 직접 해제해 주세요 (myaccount.google.com/permissions)",
          { duration: 10_000 },
        );
      },
      onError: () => toast.error("연결을 해제하지 못했습니다"),
    });
  };

  if (isConnectionPending) {
    return (
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        연동 상태를 불러오는 중...
      </p>
    );
  }

  return (
    <section className="space-y-6">
      <div className="space-y-1">
        <h2
          className="text-lg font-semibold"
          style={{
            color: "var(--text-primary)",
            fontFamily: "var(--font-display)",
          }}
        >
          팀 지식에 필요한 파일만 연결
        </h2>
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Google Drive 전체를 읽지 않습니다. 선택한 Google Docs 만 이 워크스페이스의
          AI 검색 소스로 추가됩니다.
        </p>
      </div>

      {!isConnected ? (
        <ConnectCard
          onConnect={handleConnect}
          isPending={authorize.isPending}
          isReauth={connection?.status === "reauth_required"}
        />
      ) : (
        <>
          <ImportCard
            projects={projects?.items ?? []}
            projectId={projectId}
            onProjectChange={setProjectId}
            onPick={handlePickAndImport}
            isPickerConfigured={picker.isConfigured}
            isBusy={picker.isOpening || importDocuments.isPending}
            pickerError={picker.error}
          />

          {syncRun && syncRun.status !== "completed" && syncRun.status !== "failed" && (
            <p
              className="flex items-center gap-2 text-caption"
              style={{ color: "var(--text-muted)" }}
            >
              <Loader2 size={13} className="animate-spin" aria-hidden />
              가져오는 중... ({syncRun.documents?.length ?? 0}건 처리됨)
            </p>
          )}
          {syncRun?.status === "failed" && (
            <p
              className="flex items-center gap-2 text-caption"
              style={{ color: "var(--danger, #dc2626)" }}
            >
              <AlertTriangle size={13} aria-hidden />
              {syncRun.errorSummary ?? "가져오기에 실패했습니다"}
            </p>
          )}

          {documents && documents.length > 0 && (
            <DocumentTable
              documents={documents}
              onResync={(id) =>
                resync.mutate(id, {
                  onSuccess: () => toast.success("다시 동기화를 시작했습니다"),
                  onError: () => toast.error("다시 동기화를 시작하지 못했습니다"),
                })
              }
              onUnpublish={(id) =>
                unpublish.mutate(id, {
                  onSuccess: () => toast.success("발행을 취소했습니다"),
                  onError: () => toast.error("발행을 취소하지 못했습니다"),
                })
              }
              isResyncPending={resync.isPending}
              isUnpublishPending={unpublish.isPending}
            />
          )}

          <DisconnectCard
            documentCount={documents?.length ?? 0}
            onDisconnect={handleDisconnect}
            isPending={disconnect.isPending}
          />
        </>
      )}
    </section>
  );
}

function ConnectCard({
  onConnect,
  isPending,
  isReauth,
}: {
  onConnect: () => void;
  isPending: boolean;
  isReauth: boolean;
}) {
  return (
    <div className="space-y-6">
      <div
        className="flex flex-col gap-6 rounded-lg border p-5 md:flex-row md:items-center md:justify-between"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border-subtle)",
        }}
      >
        <div className="flex items-start gap-3">
          <div
            className="flex size-9 shrink-0 items-center justify-center rounded-md text-sm font-semibold"
            style={{
              background: "var(--surface-active)",
              color: "var(--text-primary)",
            }}
          >
            G
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
              Google Drive
            </p>
            <p className="text-caption" style={{ color: "var(--text-muted)" }}>
              선택한 Google Docs 만 Kairos 에 추가
            </p>
          </div>
        </div>
        <Button onClick={onConnect} disabled={isPending}>
          {isPending ? "이동 중..." : isReauth ? "다시 연결" : "Google Drive 연결"}
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {[
          [LockKeyhole, "파일 단위 권한", "Google Picker 에서 선택한 파일만 접근"],
          [Database, "지식 복제본", "읽을 수 있는 텍스트와 메타데이터만 저장"],
          [SearchCheck, "출처 보장", "답변에 Kairos 원문과 Drive 링크를 함께 표시"],
        ].map(([Icon, title, body]) => {
          const CardIcon = Icon as typeof LockKeyhole;
          return (
            <div
              key={title as string}
              className="space-y-3 rounded-md border p-4"
              style={{
                borderColor: "var(--border-subtle)",
                background: "var(--background)",
              }}
            >
              <CardIcon size={16} style={{ color: "var(--accent)" }} aria-hidden />
              <div className="space-y-1">
                <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {title as string}
                </p>
                <p
                  className="text-caption leading-relaxed"
                  style={{ color: "var(--text-muted)" }}
                >
                  {body as string}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ImportCard({
  projects,
  projectId,
  onProjectChange,
  onPick,
  isPickerConfigured,
  isBusy,
  pickerError,
}: {
  projects: { id: string; title: string }[];
  projectId: string;
  onProjectChange: (value: string) => void;
  onPick: () => void;
  isPickerConfigured: boolean;
  isBusy: boolean;
  pickerError: string | null;
}) {
  return (
    <div
      className="space-y-4 rounded-lg border p-5"
      style={{ background: "var(--surface)", borderColor: "var(--border-subtle)" }}
    >
      <div className="space-y-1">
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Google Docs 가져오기
        </p>
        <p className="text-caption leading-relaxed" style={{ color: "var(--text-muted)" }}>
          선택한 문서는 아래 프로젝트의 공개 범위를 그대로 따릅니다. 프로젝트를
          고르지 않으면 검색에서 제외된 상태로 저장됩니다.
        </p>
      </div>

      <label className="block space-y-1.5">
        <span className="text-caption" style={{ color: "var(--text-muted)" }}>
          연결할 프로젝트
        </span>
        <select
          value={projectId}
          onChange={(event) => onProjectChange(event.target.value)}
          className="w-full rounded-md border px-3 py-2 text-sm"
          style={{
            borderColor: "var(--border)",
            background: "var(--background)",
            color: "var(--text-primary)",
          }}
        >
          <option value="">검색 제외 (프로젝트 없음)</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.title}
            </option>
          ))}
        </select>
      </label>

      <Button onClick={onPick} disabled={isBusy || !isPickerConfigured}>
        <FileText size={15} aria-hidden />
        {isBusy ? "처리 중..." : "Drive 에서 문서 선택"}
      </Button>

      {!isPickerConfigured && (
        <p className="text-caption" style={{ color: "var(--text-muted)" }}>
          이 빌드에 Google Picker 설정이 주입되지 않아 선택 창을 열 수 없습니다.
        </p>
      )}
      {pickerError && (
        <p className="text-caption" style={{ color: "var(--danger, #dc2626)" }}>
          {pickerError}
        </p>
      )}
    </div>
  );
}

function DocumentTable({
  documents,
  onResync,
  onUnpublish,
  isResyncPending,
  isUnpublishPending,
}: {
  documents: ExternalDocument[];
  onResync: (id: string) => void;
  onUnpublish: (id: string) => void;
  isResyncPending: boolean;
  isUnpublishPending: boolean;
}) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
        팀 지식 소스 ({documents.length})
      </p>
      <div
        className="overflow-hidden rounded-md border"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        {documents.map((document) => (
          <div
            key={document.id}
            className="flex flex-col gap-2 border-b px-4 py-3 last:border-b-0 sm:flex-row sm:items-center sm:justify-between"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            <div className="min-w-0 space-y-1">
              <a
                href={document.originUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="block truncate text-sm hover:underline"
                style={{ color: "var(--text-primary)" }}
              >
                {document.title}
              </a>
              <p
                className="text-caption"
                style={{
                  color: ATTENTION_STATUSES.has(document.syncStatus)
                    ? "var(--danger, #dc2626)"
                    : "var(--text-muted)",
                }}
              >
                {SYNC_STATUS_LABEL[document.syncStatus]}
                {document.lastSyncedAt
                  ? ` · ${formatDateTime(document.lastSyncedAt)}`
                  : ""}
              </p>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onResync(document.id)}
                disabled={isResyncPending}
                aria-label={`${document.title} 다시 동기화`}
              >
                <RefreshCw size={14} aria-hidden />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onUnpublish(document.id)}
                disabled={isUnpublishPending}
                aria-label={`${document.title} 발행 취소`}
              >
                <Trash2 size={14} aria-hidden />
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DisconnectCard({
  documentCount,
  onDisconnect,
  isPending,
}: {
  documentCount: number;
  onDisconnect: () => void;
  isPending: boolean;
}) {
  return (
    <div
      className="flex flex-col gap-3 rounded-lg border p-5 md:flex-row md:items-center md:justify-between"
      style={{ borderColor: "var(--border-subtle)" }}
    >
      <div className="space-y-1">
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          연결 해제
        </p>
        <p className="text-caption leading-relaxed" style={{ color: "var(--text-muted)" }}>
          {documentCount > 0
            ? `발행된 문서 ${documentCount}건이 검색에서 제거되고 본문·임베딩이 삭제됩니다.`
            : "저장된 인증 정보를 삭제하고 Google 권한을 폐기합니다."}
        </p>
      </div>
      <Button variant="destructive" onClick={onDisconnect} disabled={isPending}>
        {isPending ? "해제 중..." : "연결 해제"}
      </Button>
    </div>
  );
}
