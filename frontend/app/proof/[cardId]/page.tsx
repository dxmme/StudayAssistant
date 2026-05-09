import { ProofCheckerSession } from '@/components/ProofCheckerSession'

export default async function ProofPage({
  params,
}: {
  params: Promise<{ cardId: string }>
}) {
  const { cardId } = await params
  return <ProofCheckerSession cardId={cardId} />
}
