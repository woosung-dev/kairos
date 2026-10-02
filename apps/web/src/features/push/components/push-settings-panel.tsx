"use client";

// SCR-002 알림 설정 — `/settings?tab=notifications` (docs/requirements/pwa.md §5.6).
// 탭 노출(API-001 isEnabled)은 설정 페이지가 정한다. 이 패널은 이 기기·이 계정의 구독 상태만 다룬다.
// 등록 없음은 탭 숨김이 아니라 '사용 불가' 상태다 — 탭은 서버 값 하나에만 의존한다 (§5.6 근거).
import { usePushSettings, type PushSettingsState } from "../hooks";
import { IosInstallHint } from "./ios-install-hint";

const STATUS_TEXT: Record<PushSettingsState, string> = {
  loading: "알림 상태를 확인하는 중…",
  "ios-install": "홈 화면에 추가한 앱에서만 알림을 켤 수 있어요",
  unavailable: "이 브라우저·환경에서는 알림을 켤 수 없어요",
  denied: "브라우저 설정에서 이 사이트의 알림을 허용해 주세요",
  off: "알림이 꺼져 있어요",
  on: "알림이 켜져 있어요",
};

interface PushSettingsPanelProps {
  /** API-001 의 공개키 — `isEnabled=true` 일 때만 이 패널이 마운트된다 */
  vapidPublicKey: string | null;
}

export function PushSettingsPanel({ vapidPublicKey }: PushSettingsPanelProps) {
  const { state, isBusy, handleToggle } = usePushSettings(vapidPublicKey);
  const isOn = state === "on";
  const isToggleDisabled = isBusy || (state !== "on" && state !== "off");

  return (
    <section data-testid="push-settings" className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            회의 처리 알림
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
            업로드한 회의의 처리가 끝나거나 실패하면 이 기기로 알려드려요.
          </p>
          <p
            className="text-caption"
            style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}
          >
            이 기기·이 계정에만 적용
          </p>
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={isOn}
          aria-label="회의 처리 알림"
          data-testid="push-toggle"
          disabled={isToggleDisabled}
          onClick={handleToggle}
          className="relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            background: isOn ? "var(--accent)" : "var(--surface-active)",
            borderColor: isOn ? "var(--accent)" : "var(--border)",
          }}
        >
          <span
            aria-hidden
            className="inline-block size-3.5 rounded-full transition-transform duration-150"
            style={{
              background: isOn ? "var(--background)" : "var(--text-secondary)",
              transform: isOn ? "translateX(18px)" : "translateX(2px)",
            }}
          />
        </button>
      </div>

      <p
        data-testid="push-status"
        data-state={state}
        role="status"
        className="text-sm"
        style={{ color: state === "denied" ? "var(--warning)" : "var(--text-secondary)" }}
      >
        {STATUS_TEXT[state]}
      </p>

      {state === "ios-install" ? <IosInstallHint /> : null}
    </section>
  );
}
