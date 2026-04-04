"use client";

import { useState } from "react";
import { toast } from "sonner";

/* ── Mock 프로젝트 목록 ── */

const MOCK_PROJECTS = [
  { id: "proj-001", title: "Q2 제품 로드맵" },
  { id: "proj-002", title: "디자인 시스템" },
  { id: "proj-003", title: "DevOps 개선" },
  { id: "proj-004", title: "사용자 리서치" },
];

/* ── Mock 저장된 메모 ── */

interface SavedMemo {
  id: string;
  title: string;
  content: string;
  projectTitle: string | null;
  createdAt: string;
}

const INITIAL_MEMOS: SavedMemo[] = [
  {
    id: "memo-001",
    title: "RAG 성능 개선 아이디어",
    content: "Semantic cache를 도입하면 반복 쿼리 응답 시간을 80% 줄일 수 있을 것 같다.",
    projectTitle: "Q2 제품 로드맵",
    createdAt: "2026-03-30",
  },
  {
    id: "memo-002",
    title: "사용자 피드백 요약",
    content: "검색 기능은 만족하지만, 필터링 옵션이 부족하다는 의견이 많음.",
    projectTitle: "사용자 리서치",
    createdAt: "2026-03-28",
  },
];

/* ── 컴포넌트 ── */

export function QuickMemo() {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [memos, setMemos] = useState<SavedMemo[]>(INITIAL_MEMOS);
  const [isComposing, setIsComposing] = useState(false);

  function handleSave() {
    if (!title.trim() && !content.trim()) {
      toast.error("제목 또는 내용을 입력해주세요");
      return;
    }

    const selectedProject = MOCK_PROJECTS.find((p) => p.id === selectedProjectId);

    const newMemo: SavedMemo = {
      id: `memo-${Date.now()}`,
      title: title.trim() || "제목 없음",
      content: content.trim(),
      projectTitle: selectedProject?.title ?? null,
      createdAt: new Date().toISOString().split("T")[0],
    };

    setMemos((prev) => [newMemo, ...prev]);
    setTitle("");
    setContent("");
    setSelectedProjectId("");
    setIsComposing(false);
    toast.success("메모가 저장되었습니다");
  }

  return (
    <div className="p-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1
            className="text-2xl font-bold mb-1"
            style={{ fontFamily: "var(--font-display)", color: "var(--text-primary)" }}
          >
            빠른 메모
          </h1>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            아이디어를 빠르게 기록하세요. 마크다운 문법을 지원합니다.
          </p>
        </div>
        {!isComposing && (
          <button
            onClick={() => setIsComposing(true)}
            className="px-4 py-2 rounded text-sm font-medium transition-colors"
            style={{
              background: "var(--accent)",
              color: "var(--background)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              minHeight: "44px",
            }}
          >
            + 새 메모
          </button>
        )}
      </div>

      {/* 메모 입력 폼 */}
      {isComposing && (
        <div
          className="p-4 rounded-lg border mb-6"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
          }}
        >
          {/* 제목 */}
          <input
            type="text"
            placeholder="메모 제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-transparent text-lg font-semibold outline-none mb-3"
            style={{
              color: "var(--text-primary)",
              fontFamily: "var(--font-display)",
            }}
          />

          {/* 본문 */}
          <textarea
            placeholder="내용을 입력하세요... (마크다운 지원)"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={6}
            className="w-full bg-transparent text-sm outline-none resize-none leading-relaxed"
            style={{
              color: "var(--text-secondary)",
            }}
          />

          {/* 하단: 프로젝트 선택 + 저장 */}
          <div
            className="flex items-center justify-between mt-4 pt-3 border-t"
            style={{ borderColor: "var(--border-subtle)" }}
          >
            <div className="flex items-center gap-2">
              <label className="text-xs" style={{ color: "var(--text-muted)" }}>
                프로젝트:
              </label>
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="text-xs px-2 py-1.5 rounded border bg-transparent outline-none"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                <option value="">선택 안 함</option>
                {MOCK_PROJECTS.map((proj) => (
                  <option key={proj.id} value={proj.id}>
                    {proj.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setIsComposing(false);
                  setTitle("");
                  setContent("");
                  setSelectedProjectId("");
                }}
                className="px-3 py-1.5 rounded text-xs font-medium transition-colors border"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--text-muted)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                취소
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-1.5 rounded text-xs font-medium transition-colors"
                style={{
                  background: "var(--accent)",
                  color: "var(--background)",
                  borderRadius: "var(--radius-sm)",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                저장
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 저장된 메모 목록 */}
      {memos.length > 0 ? (
        <div className="grid gap-3">
          {memos.map((memo) => (
            <MemoCard key={memo.id} memo={memo} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <span className="text-4xl mb-4">📝</span>
          <h3
            className="text-lg font-semibold mb-2"
            style={{ color: "var(--text-primary)", fontFamily: "var(--font-display)" }}
          >
            아직 메모가 없습니다
          </h3>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            빠른 메모를 작성하면 AI가 자동으로 프로젝트에 연결합니다
          </p>
        </div>
      )}
    </div>
  );
}

/* ── 서브 컴포넌트 ── */

function MemoCard({ memo }: { memo: SavedMemo }) {
  return (
    <div
      className="p-4 rounded-lg border transition-colors"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border-subtle)",
        borderRadius: "var(--radius-lg)",
        cursor: "pointer",
      }}
      onMouseOver={(e) => (e.currentTarget.style.borderColor = "var(--accent)")}
      onMouseOut={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
    >
      <div className="flex items-start justify-between mb-1">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {memo.title}
        </h3>
        <span className="text-[10px] shrink-0 ml-2" style={{ color: "var(--text-muted)" }}>
          {memo.createdAt}
        </span>
      </div>
      <p className="text-xs line-clamp-2 mb-2" style={{ color: "var(--text-secondary)" }}>
        {memo.content}
      </p>
      {memo.projectTitle && (
        <span
          className="px-1.5 py-0.5 rounded text-[10px]"
          style={{
            background: "var(--accent-subtle)",
            color: "var(--accent)",
          }}
        >
          {memo.projectTitle}
        </span>
      )}
    </div>
  );
}
