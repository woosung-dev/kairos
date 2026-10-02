// REQ-011 iOS 설치 안내 — iOS·iPadOS 의 홈 화면 앱이 아닐 때만 SCR-002 안에 보인다
// (docs/requirements/pwa.md §5.6, Next 번들 문서 progressive-web-apps.md:88 — iOS 16.4+ 는 홈 화면 앱에서만 푸시).
// 표시 조건 판정은 utils.ts `shouldShowIosInstallHint` 가 한다. 커스텀 설치 버튼은 만들지 않는다 (BL-PWA-1).
import { Share } from "lucide-react";

export function IosInstallHint() {
  return (
    <div
      data-testid="ios-install-hint"
      className="flex items-start gap-3 rounded-md border p-4"
      style={{ background: "var(--surface)", borderColor: "var(--border-subtle)" }}
    >
      <Share className="mt-0.5 size-4 shrink-0" aria-hidden style={{ color: "var(--accent)" }} />
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
        iPhone·iPad 는 홈 화면에 추가한 Kairos 에서만 알림을 받을 수 있어요 (iOS 16.4 이상). Safari
        공유 버튼 → &apos;홈 화면에 추가&apos; 후 그 앱에서 알림을 켜 주세요.
      </p>
    </div>
  );
}
