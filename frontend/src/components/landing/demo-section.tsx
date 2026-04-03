export function DemoSection() {
  return (
    <section
      id="demo"
      className="px-6 py-24"
      style={{ background: "var(--surface)" }}
    >
      <div className="max-w-5xl mx-auto">
        <h2
          className="text-center mb-4"
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: "32px",
            color: "var(--text-primary)",
          }}
        >
          하나의 질문으로
          <br />
          팀의 모든 지식에 접근하세요
        </h2>
        <p
          className="text-center mb-12"
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "16px",
            color: "var(--text-secondary)",
          }}
        >
          회의에서 논의된 내용, 작성한 노트, 공유한 자료를 AI가 통합 검색합니다
        </p>

        {/* 브라우저 프레임 목업 */}
        <div
          className="rounded-xl border overflow-hidden shadow-2xl"
          style={{
            borderColor: "var(--border)",
            borderRadius: "12px",
          }}
        >
          {/* 브라우저 탑바 */}
          <div
            className="flex items-center gap-2 px-4 py-3 border-b"
            style={{
              background: "var(--surface-hover)",
              borderColor: "var(--border-subtle)",
            }}
          >
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ background: "#FF5F56" }} />
              <div className="w-3 h-3 rounded-full" style={{ background: "#FFBD2E" }} />
              <div className="w-3 h-3 rounded-full" style={{ background: "#27C93F" }} />
            </div>
            <div
              className="flex-1 text-center text-xs"
              style={{
                color: "var(--text-muted)",
                fontFamily: "var(--font-mono)",
              }}
            >
              kairos.app
            </div>
          </div>

          {/* 앱 UI 목업 (다크모드 — 실제 앱처럼) */}
          <div
            className="flex"
            style={{
              background: "#0A0A0B",
              height: "420px",
            }}
          >
            {/* 사이드바 */}
            <div
              className="w-48 shrink-0 border-r p-3"
              style={{ borderColor: "#1E1E22" }}
            >
              <div
                className="text-sm font-bold mb-4"
                style={{ color: "#3ECFB4", fontFamily: "var(--font-display)" }}
              >
                K
              </div>
              {["홈", "Inbox", "노트", "검색"].map((item) => (
                <div
                  key={item}
                  className="text-xs py-1.5 px-2 rounded mb-0.5"
                  style={{ color: "#8E8E93" }}
                >
                  {item}
                </div>
              ))}
              <div className="mt-4 text-[10px] uppercase" style={{ color: "#5C5C63" }}>
                프로젝트
              </div>
              {["CMS 고도화", "보안 인프라"].map((p) => (
                <div
                  key={p}
                  className="text-xs py-1 px-2"
                  style={{ color: "#8E8E93" }}
                >
                  {p}
                </div>
              ))}
            </div>

            {/* 메인 */}
            <div className="flex-1 p-4">
              <div
                className="text-lg font-bold mb-6"
                style={{ color: "#EDEDEF", fontFamily: "var(--font-display)" }}
              >
                무엇이든 질문하세요
              </div>
              <div className="space-y-3">
                <div className="flex justify-end">
                  <div
                    className="px-3 py-2 rounded text-sm max-w-[70%]"
                    style={{
                      background: "rgba(62,207,180,0.1)",
                      color: "#EDEDEF",
                      borderRadius: "6px",
                    }}
                  >
                    CMS 보안검토에서 어떤 결정이 있었어?
                  </div>
                </div>
                <div
                  className="px-3 py-2 rounded text-sm max-w-[80%]"
                  style={{
                    background: "#141416",
                    color: "#EDEDEF",
                    borderRadius: "6px",
                  }}
                >
                  CMS 보안검토에서는 다음 결정이 있었습니다.
                  <br />
                  <br />
                  • jwt 인증 방식을 도입하기로 결정했습니다.
                  <br />
                  <br />
                  <span style={{ color: "#5C5C63", fontSize: "11px" }}>
                    📎 test-meeting (2026-04-02)
                  </span>
                </div>
              </div>
            </div>

            {/* RAG 패널 */}
            <div
              className="w-56 shrink-0 border-l p-3"
              style={{ borderColor: "#1E1E22" }}
            >
              <div
                className="text-xs font-semibold mb-3"
                style={{ color: "#EDEDEF", fontFamily: "var(--font-display)" }}
              >
                지식 검색
              </div>
              <div className="text-[10px]" style={{ color: "#5C5C63" }}>
                프로젝트에 대해 질문하세요
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
