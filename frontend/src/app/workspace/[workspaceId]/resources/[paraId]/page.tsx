import { ParaDetail } from "@/features/para/components/para-detail";

export default async function ResourceDetailPage({
  params,
}: {
  params: Promise<{ paraId: string }>;
}) {
  const { paraId } = await params;
  return <ParaDetail paraId={paraId} />;
}
