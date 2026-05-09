import { ReviewSession } from '@/components/ReviewSession'

export default async function ReviewPage({
  params,
}: {
  params: Promise<{ courseId: string }>
}) {
  const { courseId } = await params
  return <ReviewSession courseId={courseId} />
}
