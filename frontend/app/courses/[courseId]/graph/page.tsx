import { ConceptGraph } from '@/components/ConceptGraph'

export default async function GraphPage({
  params,
}: {
  params: Promise<{ courseId: string }>
}) {
  const { courseId } = await params
  return <ConceptGraph courseId={courseId} />
}
