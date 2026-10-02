import { MeetingDetail } from "@/features/meetings/components/meeting-detail";

export default async function MeetingDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ id }, { workspace }] = await Promise.all([params, searchParams]);
  // 알림 딥링크 `?workspace=<wid>` (pwa.md §5.5). 중복 파라미터(배열)는 비UUID 와 같이 제거 대상이다.
  const workspaceParam = workspace === undefined ? null : typeof workspace === "string" ? workspace : "";
  return <MeetingDetail meetingId={id} workspaceParam={workspaceParam} />;
}
