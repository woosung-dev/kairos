"use client";

import {
  ArrowRight,
  CheckCircle2,
  Cloud,
  Database,
  FileText,
  FolderOpen,
  LockKeyhole,
  RefreshCw,
  SearchCheck,
  ShieldCheck,
} from "lucide-react";
import {
  PrototypeSwitcher,
  type PrototypeVariant,
} from "@/components/shared/prototype-switcher";

// Three variants of the settings integration page, switchable via ?variant=,
// on the existing /settings route. This is development-only throwaway UI.
const DRIVE_VARIANTS = [
  { key: "A", label: "권한 우선" },
  { key: "B", label: "가져오기 흐름" },
  { key: "C", label: "지식 현황" },
] as const satisfies readonly PrototypeVariant[];

interface GoogleDrivePrototypeProps {
  workspaceName: string;
  variant: string | null;
}

function PrototypeBadge() {
  return (
    <span
      className="rounded px-1.5 py-0.5 text-micro"
      style={{
        background: "var(--accent-subtle)",
        color: "var(--accent)",
        fontFamily: "var(--font-mono)",
      }}
    >
      PROTOTYPE · API 없음
    </span>
  );
}

function SectionTitle({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="space-y-1">
      <h2
        className="text-lg font-semibold"
        style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
      >
        {title}
      </h2>
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
        {description}
      </p>
    </div>
  );
}

function StaticCta({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium"
      style={{ background: "var(--accent)", color: "var(--background)" }}
    >
      {children}
      <ArrowRight size={15} aria-hidden />
    </div>
  );
}

function VariantA({ workspaceName }: { workspaceName: string }) {
  return (
    <div className="space-y-6">
      <SectionTitle
        title="팀 지식에 필요한 파일만 연결"
        description="Google Drive 전체를 읽지 않고, 관리자가 선택한 문서만 이 워크스페이스의 AI 검색 소스로 추가합니다."
      />
      <div
        className="flex flex-col gap-6 rounded-lg border p-5 md:flex-row md:items-center md:justify-between"
        style={{ background: "var(--surface)", borderColor: "var(--border-subtle)" }}
      >
        <div className="flex items-start gap-3">
          <div
            className="flex size-9 shrink-0 items-center justify-center rounded-md text-sm font-semibold"
            style={{ background: "var(--surface-active)", color: "var(--text-primary)" }}
          >
            G
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
              Google Drive
            </p>
            <p className="text-caption" style={{ color: "var(--text-muted)" }}>
              선택한 Docs · PDF · Markdown만 Kairos에 추가
            </p>
          </div>
        </div>
        <StaticCta>Google Drive 연결</StaticCta>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {[
          [LockKeyhole, "파일 단위 권한", "Google Picker에서 선택한 파일만 접근"],
          [Database, "지식 복제본", "읽기 가능한 텍스트와 메타데이터만 저장"],
          [SearchCheck, "출처 보장", "답변에서 Kairos 원문과 Drive 링크를 함께 표시"],
        ].map(([Icon, title, body]) => {
          const CardIcon = Icon as typeof LockKeyhole;
          return (
            <div
              key={title as string}
              className="space-y-3 rounded-md border p-4"
              style={{ borderColor: "var(--border-subtle)", background: "var(--background)" }}
            >
              <CardIcon size={16} style={{ color: "var(--accent)" }} aria-hidden />
              <div className="space-y-1">
                <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {title as string}
                </p>
                <p className="text-caption leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {body as string}
                </p>
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-caption" style={{ color: "var(--text-muted)" }}>
        상태 가정 · {workspaceName}의 owner가 개인 Google 계정으로 명시 선택 · 최초 동기화는 수동 시작
      </p>
    </div>
  );
}

function VariantB() {
  const steps = [
    ["01", Cloud, "연결", "Google 계정을 연결하고, Kairos가 요청할 범위를 확인합니다."],
    ["02", FolderOpen, "선택", "파일 또는 폴더를 고릅니다. 선택된 하위 파일 수를 보여줍니다."],
    ["03", Database, "팀 지식화", "텍스트 추출 → 프로젝트 연결 → 임베딩이 백그라운드에서 진행됩니다."],
  ] as const;

  return (
    <div className="space-y-6">
      <SectionTitle
        title="한 번에 하나의 의도를 끝내는 가져오기"
        description="연결 설정을 먼저 끝내는 대신, 사용자가 ‘무엇이 팀 지식이 되는지’를 각 단계에서 분명히 확인합니다."
      />
      <ol className="space-y-0">
        {steps.map(([number, Icon, title, body], index) => (
          <li key={number} className="relative flex gap-4 pb-7 last:pb-0">
            {index < steps.length - 1 && (
              <div
                className="absolute left-4 top-9 h-[calc(100%-20px)] border-l"
                style={{ borderColor: "var(--border)" }}
              />
            )}
            <div
              className="z-10 flex size-8 shrink-0 items-center justify-center rounded-full text-caption"
              style={{ background: "var(--surface-active)", color: "var(--accent)" }}
            >
              {number}
            </div>
            <div className="flex-1 border-b pb-7 last:border-b-0 last:pb-0" style={{ borderColor: "var(--border-subtle)" }}>
              <div className="flex flex-wrap items-center gap-2">
                <Icon size={16} style={{ color: "var(--text-secondary)" }} aria-hidden />
                <h3 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {title}
                </h3>
                {index === 0 && <PrototypeBadge />}
              </div>
              <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                {body}
              </p>
              {index === 1 && (
                <div
                  className="mt-3 flex items-center gap-2 rounded-md px-3 py-2 text-caption"
                  style={{ background: "var(--surface)", color: "var(--text-secondary)" }}
                >
                  <FileText size={14} aria-hidden />
                  예시 · 제품 전략 / 2026 Q3 / 14개 파일
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
      <div
        className="flex items-start gap-3 rounded-md border p-4"
        style={{ borderColor: "var(--border-subtle)", background: "var(--surface)" }}
      >
        <ShieldCheck size={17} style={{ color: "var(--accent)" }} aria-hidden />
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          팀에 공개하기 전, 선택 파일을 어느 Project에 연결할지와 전체 Workspace 검색 포함 여부를 정합니다.
        </p>
      </div>
    </div>
  );
}

function VariantC({ workspaceName }: { workspaceName: string }) {
  const sourceRows = [
    ["제품 전략 / 2026 Q3", "14개 파일", "프로젝트: Kairos", "준비됨"],
    ["고객 인터뷰", "8개 파일", "전체 Workspace", "다음 동기화 대기"],
    ["채용 운영", "3개 파일", "RAG 제외", "보관"],
  ] as const;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <SectionTitle
          title="팀 지식 소스"
          description="연결 후에는 OAuth 자체보다 어떤 자료가 검색되고, 얼마나 최신인지가 핵심입니다."
        />
        <div className="flex items-center gap-2 text-caption" style={{ color: "var(--text-muted)" }}>
          <RefreshCw size={13} aria-hidden />
          마지막 동기화 · 2026-07-30 10:42
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {[
          ["25", "검색 가능한 파일"],
          ["3", "연결된 프로젝트"],
          ["1", "검토가 필요한 변경"],
        ].map(([value, label]) => (
          <div
            key={label}
            className="rounded-md border p-4"
            style={{ borderColor: "var(--border-subtle)", background: "var(--surface)" }}
          >
            <p className="text-xl font-semibold" style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
              {value}
            </p>
            <p className="mt-1 text-caption" style={{ color: "var(--text-muted)" }}>{label}</p>
          </div>
        ))}
      </div>
      <div className="overflow-hidden rounded-md border" style={{ borderColor: "var(--border-subtle)" }}>
        <div
          className="grid grid-cols-[minmax(0,1.5fr)_auto] gap-3 px-4 py-2 text-caption md:grid-cols-[minmax(0,1.5fr)_110px_140px_130px]"
          style={{ background: "var(--surface-active)", color: "var(--text-muted)" }}
        >
          <span>선택한 Drive 소스</span><span className="hidden md:block">범위</span><span className="hidden md:block">대상</span><span>상태</span>
        </div>
        {sourceRows.map(([name, count, scope, status]) => (
          <div
            key={name}
            className="grid grid-cols-[minmax(0,1.5fr)_auto] gap-3 border-t px-4 py-3 text-sm md:grid-cols-[minmax(0,1.5fr)_110px_140px_130px]"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            <span className="truncate" style={{ color: "var(--text-primary)" }}>{name}</span>
            <span className="hidden text-caption md:block" style={{ color: "var(--text-muted)" }}>{count}</span>
            <span className="hidden truncate text-caption md:block" style={{ color: "var(--text-muted)" }}>{scope}</span>
            <span className="flex items-center gap-1 text-caption" style={{ color: status === "준비됨" ? "var(--accent)" : "var(--text-muted)" }}>
              {status === "준비됨" && <CheckCircle2 size={13} aria-hidden />}{status}
            </span>
          </div>
        ))}
      </div>
      <p className="text-caption" style={{ color: "var(--text-muted)" }}>
        상태 가정 · {workspaceName}에 이미 선택형 Drive 소스가 존재하며, 원본 삭제·권한 회수 시 검색 대상에서도 제거
      </p>
    </div>
  );
}

export function GoogleDrivePrototype({
  workspaceName,
  variant,
}: GoogleDrivePrototypeProps) {
  const requestedVariant = variant ?? "A";
  const activeVariant = DRIVE_VARIANTS.some((item) => item.key === requestedVariant)
    ? requestedVariant
    : "A";

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-3 border-b pb-4" style={{ borderColor: "var(--border-subtle)" }}>
        <div className="flex items-center gap-2">
          <PrototypeBadge />
          <span className="text-caption" style={{ color: "var(--text-muted)" }}>
            Google Drive 팀 지식 연동 UI 가설
          </span>
        </div>
        <span className="text-caption" style={{ color: "var(--text-muted)" }}>
          ← → 로 비교
        </span>
      </div>
      {activeVariant === "A" && <VariantA workspaceName={workspaceName} />}
      {activeVariant === "B" && <VariantB />}
      {activeVariant === "C" && <VariantC workspaceName={workspaceName} />}
      <PrototypeSwitcher variants={DRIVE_VARIANTS} currentVariant={activeVariant} />
    </section>
  );
}
