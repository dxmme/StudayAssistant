export interface FsrsState {
  due: string
  stability?: number | null
  difficulty?: number | null
  state?: number | null
  step?: number | null
  last_review?: string | null
  card_id?: string
}

export interface Card {
  id: string
  course_id: string
  concept_id?: string | null
  type: string
  front: string
  back: string
  bloom_level?: number | null
  fsrs_state: FsrsState
  review_count: number
  lapse_count: number
  created_at?: string | null
  archived: boolean
}

export interface ReviewResponse {
  card_id: string
  fsrs_state: FsrsState
  next_due: string
  lapse_count: number
  review_count: number
}
