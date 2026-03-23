import { ParaDetail } from "@/features/para/components/para-detail";

export default async function AreaDetailPage({
  params,
}: {
  params: Promise<{ paraId: string }>;
}) {
  const { paraId } = await params;
  return <ParaDetail paraId={paraId} />;
}
