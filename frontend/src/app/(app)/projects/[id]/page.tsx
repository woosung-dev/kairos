import { ProjectDashboard } from "@/features/projects/components/project-dashboard";

export default async function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ProjectDashboard projectId={id} />;
}
