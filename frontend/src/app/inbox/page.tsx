import { InboxList } from "@/features/inbox/components/inbox-list";

export default function InboxPage() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Inbox</h1>
        <p className="text-sm text-muted-foreground">
          분류되지 않은 아이템을 확인하고 PARA 카테고리로 분류하세요.
        </p>
      </div>

      <InboxList />
    </div>
  );
}
