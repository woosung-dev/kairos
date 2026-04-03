import { FileText, FolderOpen, Mic, Search } from "lucide-react";

const FEATURES = [
  {
    icon: Mic,
    title: "AI 회의 요약",
    description:
      "녹음 파일을 올리면 자동으로 트랜스크립트를 생성하고 핵심 내용, 액션 아이템, 결정 사항을 정리합니다",
  },
  {
    icon: Search,
    title: "지식 검색",
    description:
      "회의록, 노트, 자료를 한 번에 검색합니다. AI가 맥락을 이해하고 출처와 함께 답변합니다",
  },
  {
    icon: FileText,
    title: "스마트 노트",
    description:
      "프로젝트별로 노트를 정리하세요. 작성한 내용은 자동으로 임베딩되어 검색 가능한 지식이 됩니다",
  },
  {
    icon: FolderOpen,
    title: "프로젝트 관리",
    description:
      "프로젝트 중심으로 회의, 노트, 자료를 구조화합니다. 태그와 AI 자동 분류로 정리가 쉬워집니다",
  },
];

export function FeaturesSection() {
  return (
    <section
      id="features"
      className="px-6 py-24"
      style={{ background: "var(--background)" }}
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
          똑똑해지는 팀을 위한 도구
        </h2>
        <p
          className="text-center mb-16"
          style={{
            fontFamily: "var(--font-body)",
            fontSize: "16px",
            color: "var(--text-secondary)",
          }}
        >
          회의부터 검색까지, AI가 팀의 지식을 복리로 쌓아줍니다
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="p-6 rounded-lg border transition-shadow hover:shadow-lg"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
              }}
            >
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                style={{
                  background: "var(--accent-subtle)",
                  borderRadius: "var(--radius-md)",
                }}
              >
                <feature.icon
                  size={20}
                  style={{ color: "var(--accent)" }}
                />
              </div>
              <h3
                className="mb-2"
                style={{
                  fontFamily: "var(--font-display)",
                  fontWeight: 600,
                  fontSize: "18px",
                  color: "var(--text-primary)",
                }}
              >
                {feature.title}
              </h3>
              <p
                className="text-sm leading-relaxed"
                style={{
                  fontFamily: "var(--font-body)",
                  color: "var(--text-secondary)",
                }}
              >
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
