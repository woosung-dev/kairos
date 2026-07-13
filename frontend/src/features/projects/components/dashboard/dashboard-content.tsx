// 대시보드 본문 — 최근 회의/노트 조회 소유 + '콘텐츠 3개 미만 → 온보딩 뷰' 게이트 (BL-AV-1 분해)
"use client";

import { Skeleton } from "@/components/ui/skeleton";
import { useActionItems } from "@/features/actions/hooks";
import { useMeetings } from "@/features/meetings/hooks";
import { useNotes } from "@/features/notes/hooks";
import { useRecentItems } from "../../hooks";
import { ActionsSection } from "./actions-section";
import { MeetingCard } from "./meeting-card";
import { NoteCard } from "./note-card";
import { OnboardingView } from "./onboarding-view";

export function DashboardContent({
  wid,
  projectId,
  children,
}: {
  wid: string | undefined;
  projectId: string;
  /** 온보딩 게이트 통과(로딩 중 포함) 시에만 렌더되는 하위 섹션 — 멤버 패널/관리 다이얼로그. */
  children?: React.ReactNode;
}) {
  /* 회의: projectId 필터 지원 */
  const { data: meetingsData, isLoading: meetingsLoading } = useMeetings(wid, 1, projectId);

  /* 노트 목록: projectId 필터 지원 */
  const { data: notesData, isLoading: notesLoading } = useNotes(wid, projectId);

  /* 액션 로딩 상태 — 원본 거동 보존: 게이트/스켈레톤은 actions 포함 3종 로딩을 함께 본다.
     데이터·mutation 소유는 ActionsSection — 동일 queryKey 라 fetch 는 1회로 dedupe. */
  const { isLoading: actionsLoading } = useActionItems(wid, {
    projectId,
    page: 1,
    pageSize: 20,
  });

  const projectMeetings = meetingsData?.items ?? [];
  const notes = notesData?.items ?? [];

  /* 최근 아이템: 회의 + 노트 합쳐 날짜순 정렬, 5개 — hooks.ts:useRecentItems */
  const recentItems = useRecentItems(projectMeetings, notes);

  const isContentLoading = actionsLoading || meetingsLoading || notesLoading;

  /* 콘텐츠 3개 미만이면 온보딩 뷰 — 멤버 패널/다이얼로그(children)는 렌더하지 않는다 (원본 거동). */
  if (!isContentLoading && recentItems.length < 3) {
    return <OnboardingView />;
  }

  return (
    <>
      {/* 프로액티브 인사이트 — BE 미지원, 섹션 숨김 */}
      {/* project 응답에 insight 필드가 추가되면 여기서 렌더링 */}

      {/* 로딩 중이면 스켈레톤 */}
      {isContentLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 rounded-lg" />
            ))}
          </div>
        </div>
      ) : (
        /* 2컬럼 그리드 */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* 좌: 최근 회의/노트 */}
          <div className="space-y-3">
            <h2
              className="text-sm font-semibold mb-1"
              style={{ color: "var(--text-secondary)", fontFamily: "var(--font-display)" }}
            >
              최근 회의 &middot; 노트
            </h2>
            {recentItems.length === 0 ? (
              <p className="text-xs py-4" style={{ color: "var(--text-muted)" }}>
                최근 항목이 없습니다
              </p>
            ) : (
              recentItems.map((item) =>
                item.kind === "meeting" ? (
                  <MeetingCard key={`m-${item.data.id}`} meeting={item.data} />
                ) : (
                  <NoteCard key={`n-${item.data.id}`} note={item.data} />
                )
              )
            )}
          </div>

          {/* 우: 이번 주 액션 */}
          <ActionsSection wid={wid} projectId={projectId} />
        </div>
      )}

      {children}
    </>
  );
}
