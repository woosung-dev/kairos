import { PanelLayout } from "@/components/layout/panel-layout";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <PanelLayout>{children}</PanelLayout>;
}
