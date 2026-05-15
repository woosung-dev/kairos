import { PanelLayout } from "@/components/layout/panel-layout";
import { QueryProvider } from "@/lib/query-client";
import { Toaster } from "@/components/ui/sonner";

// ThemeProvider 는 app/layout.tsx root 로 이동 (next-themes inline script
// 경고 회피). 본 (app) 그룹은 QueryProvider + PanelLayout 만 wrap.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <QueryProvider>
      <PanelLayout>{children}</PanelLayout>
      <Toaster />
    </QueryProvider>
  );
}
