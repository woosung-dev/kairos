// /actions 진입 시 /inbox 으로 redirect — Sprint 27d BUG-S27d-2 fix
// 외부 북마크/링크가 남아 있을 가능성 대비 404 회피. inbox 가 action item 통합 뷰.
import { redirect } from "next/navigation";

export default function ActionsPage() {
  redirect("/inbox");
}
