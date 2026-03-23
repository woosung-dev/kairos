import { Inbox, Target, CalendarCheck, Mic } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const stats = [
  {
    title: "미분류 Inbox",
    value: "5",
    description: "분류 대기 아이템",
    icon: Inbox,
  },
  {
    title: "활성 프로젝트",
    value: "3",
    description: "진행 중인 프로젝트",
    icon: Target,
  },
  {
    title: "이번 주 회의",
    value: "7",
    description: "기록된 회의",
    icon: Mic,
  },
  {
    title: "대기 액션",
    value: "12",
    description: "미완료 액션 아이템",
    icon: CalendarCheck,
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">대시보드</h1>
        <p className="text-sm text-muted-foreground">
          Kairos에 오신 것을 환영합니다. 오늘의 업무를 확인하세요.
        </p>
      </div>

      {/* 통계 카드 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 빈 상태 안내 */}
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Mic className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="mt-4 text-lg font-semibold">첫 회의를 기록해보세요</h3>
          <p className="mt-1 max-w-sm text-center text-sm text-muted-foreground">
            회의를 녹음하거나 파일을 업로드하면 AI가 자동으로 요약하고
            액션 아이템을 추출합니다.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
