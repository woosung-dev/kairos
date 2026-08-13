// 노트 상세 라우트 — Sprint 24 Wave 2 T-NOTE-DETAIL (BUG-POW-003)
import { NoteDetail } from "@/features/notes/components/note-detail";

export default async function NoteDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <NoteDetail noteId={id} />;
}
