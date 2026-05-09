import { CoachingSession } from '@/components/CoachingSession'

export default async function CoachPage({
  params,
}: {
  params: Promise<{ courseId: string; conceptId: string }>
}) {
  const { courseId, conceptId } = await params
  return <CoachingSession courseId={courseId} conceptId={conceptId} />
}
