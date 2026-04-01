"use client";

import { useState } from "react";

const CONTENT_TYPES = [
  {
    id: "meeting",
    icon: "🎙️",
    title: "회의 녹음",
    description: "회의를 녹음하면 AI가 자동으로 요약하고 액션 아이템을 추출합니다",
  },
  {
    id: "note",
    icon: "📝",
    title: "노트 작성",
    description: "아이디어, 메모, 회의록을 자유롭게 작성하세요",
  },
  {
    id: "attachment",
    icon: "📎",
    title: "자료 업로드",
    description: "문서, PDF, 이미지 등 프로젝트 관련 자료를 업로드하세요",
  },
] as const;

type ContentType = (typeof CONTENT_TYPES)[number]["id"];

export default function NewContentPage() {
  const [selected, setSelected] = useState<ContentType | null>(null);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1
          className="text-2xl font-bold mb-1"
          style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
        >
          콘텐츠 추가
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          프로젝트에 추가할 콘텐츠 유형을 선택하세요
        </p>
      </div>

      {/* 유형 선택 카드 */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {CONTENT_TYPES.map((type) => (
          <button
            key={type.id}
            onClick={() => setSelected(type.id)}
            className="p-6 rounded border text-left transition-colors"
            style={{
              background: selected === type.id ? "var(--surface-hover)" : "var(--surface)",
              borderColor: selected === type.id ? "var(--accent)" : "var(--border-subtle)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <span className="text-3xl mb-3 block">{type.icon}</span>
            <h3
              className="text-sm font-semibold mb-1"
              style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
            >
              {type.title}
            </h3>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {type.description}
            </p>
          </button>
        ))}
      </div>

      {/* 선택된 유형의 폼 (빈 껍데기) */}
      {selected && (
        <div
          className="p-6 rounded border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <h2
            className="text-lg font-semibold mb-4"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            {CONTENT_TYPES.find((t) => t.id === selected)?.title}
          </h2>

          {selected === "meeting" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
                  회의 제목
                </label>
                <input
                  type="text"
                  placeholder="회의 제목을 입력하세요"
                  className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none"
                  style={{
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-sm)",
                  }}
                />
              </div>
              <div
                className="flex items-center justify-center h-32 rounded border-2 border-dashed"
                style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
              >
                <p className="text-sm">녹음 파일을 드래그하거나 클릭하여 업로드</p>
              </div>
            </div>
          )}

          {selected === "note" && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
                  노트 제목
                </label>
                <input
                  type="text"
                  placeholder="노트 제목을 입력하세요"
                  className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none"
                  style={{
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-sm)",
                  }}
                />
              </div>
              <div>
                <label className="block text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
                  내용
                </label>
                <textarea
                  placeholder="노트 내용을 입력하세요..."
                  rows={8}
                  className="w-full px-3 py-2 rounded border text-sm bg-transparent outline-none resize-none"
                  style={{
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                    borderRadius: "var(--radius-sm)",
                  }}
                />
              </div>
            </div>
          )}

          {selected === "attachment" && (
            <div
              className="flex items-center justify-center h-40 rounded border-2 border-dashed"
              style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
            >
              <div className="text-center">
                <span className="text-3xl mb-2 block">📎</span>
                <p className="text-sm">파일을 드래그하거나 클릭하여 업로드</p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  PDF, DOCX, PNG, JPG (최대 50MB)
                </p>
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-end">
            <button
              className="px-4 py-2 rounded text-sm font-medium"
              style={{
                background: "var(--accent)",
                color: "var(--background)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              추가하기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
