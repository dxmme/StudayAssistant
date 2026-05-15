'use client'

import Link from 'next/link'
import React, { useEffect, useRef, useState } from 'react'

const API = 'http://localhost:8000'

type MaterialType = 'lecture_slides' | 'script' | 'past_exam' | 'topic_overview'

interface Material {
  id: string
  title: string
  type: MaterialType
  page_count: number | null
  indexed: boolean
  uploaded_at: string
  parse_status: 'pending' | 'done' | 'error'
}

interface IngestStatusEntry {
  status: 'idle' | 'running' | 'done' | 'error'
  error?: string
}

interface IngestStatus {
  [materialId: string]: IngestStatusEntry
}

interface UploadItem {
  file: File
  type: MaterialType
  status: 'pending' | 'uploading' | 'done' | 'error'
  error?: string
}

const TYPE_LABELS: Record<MaterialType, string> = {
  lecture_slides: 'Folien',
  script: 'Skript',
  past_exam: 'Altklausur',
  topic_overview: 'Übersicht',
}

interface MaterialsPageProps {
  params: Promise<{ courseId: string }>
}

export default function MaterialsPage({ params }: MaterialsPageProps) {
  const { courseId } = React.use(params)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [materials, setMaterials] = useState<Material[]>([])
  const [loadingMaterials, setLoadingMaterials] = useState(true)
  const [uploadQueue, setUploadQueue] = useState<UploadItem[]>([])
  const [uploading, setUploading] = useState(false)
  const [ingestStatus, setIngestStatus] = useState<IngestStatus>({})
  const [defaultType, setDefaultType] = useState<MaterialType>('lecture_slides')

  useEffect(() => {
    loadMaterials()
  }, [courseId])

  function loadMaterials() {
    setLoadingMaterials(true)
    fetch(`${API}/api/courses/${courseId}/materials`)
      .then(r => r.json())
      .then(setMaterials)
      .catch(() => setMaterials([]))
      .finally(() => setLoadingMaterials(false))
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? [])
    if (files.length === 0) return
    const remaining = 20 - uploadQueue.length
    const toAdd = files.slice(0, remaining).map(f => ({
      file: f,
      type: defaultType,
      status: 'pending' as const,
    }))
    setUploadQueue(prev => [...prev, ...toAdd])
    e.target.value = ''
  }

  function removeFromQueue(index: number) {
    setUploadQueue(prev => prev.filter((_, i) => i !== index))
  }

  function updateQueueType(index: number, type: MaterialType) {
    setUploadQueue(prev => prev.map((item, i) => i === index ? { ...item, type } : item))
  }

  async function handleUpload() {
    const pending = uploadQueue.filter(i => i.status === 'pending')
    if (pending.length === 0) return
    setUploading(true)

    // Mark all pending as uploading at once
    setUploadQueue(prev => prev.map(it => it.status === 'pending' ? { ...it, status: 'uploading' as const } : it))

    // Upload all files in parallel — backend returns immediately (parse runs in background)
    const uploads = uploadQueue
      .map((item, idx) => ({ item, idx }))
      .filter(({ item }) => item.status === 'uploading' || item.status === 'pending')

    await Promise.all(uploads.map(async ({ item, idx }) => {
      const form = new FormData()
      form.append('file', item.file)
      form.append('type', item.type)
      form.append('title', item.file.name.replace(/\.pdf$/i, ''))

      try {
        const res = await fetch(`${API}/api/courses/${courseId}/materials`, {
          method: 'POST',
          body: form,
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Upload fehlgeschlagen' }))
          throw new Error(typeof err.detail === 'string' ? err.detail : 'Upload fehlgeschlagen')
        }
        const material: Material = await res.json()
        setMaterials(prev => [...prev, material])
        setUploadQueue(prev => prev.map((it, i) => i === idx ? { ...it, status: 'done' as const } : it))
        // Start polling parse status for this material
        pollParseStatus(material.id)
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Fehler'
        setUploadQueue(prev => prev.map((it, i) => i === idx ? { ...it, status: 'error' as const, error: msg } : it))
      }
    }))

    setUploading(false)
  }

  function pollParseStatus(materialId: string) {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/materials/${materialId}/parse-status`)
        if (!res.ok) { clearInterval(interval); return }
        const data: { status: string } = await res.json()
        if (data.status === 'done' || data.status === 'error') {
          setMaterials(prev => prev.map(m =>
            m.id === materialId ? { ...m, parse_status: data.status as Material['parse_status'] } : m
          ))
          clearInterval(interval)
        }
      } catch {
        clearInterval(interval)
      }
    }, 3000)
  }

  function clearDoneFromQueue() {
    setUploadQueue(prev => prev.filter(i => i.status !== 'done'))
  }

  async function handleIngest(materialId: string) {
    setIngestStatus(prev => ({ ...prev, [materialId]: { status: 'running' } }))
    try {
      const res = await fetch(`${API}/api/materials/${materialId}/ingest`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(typeof err.detail === 'string' ? err.detail : 'Ingest fehlgeschlagen')
      }
      setMaterials(prev => prev.map(m => m.id === materialId ? { ...m, indexed: true } : m))
      setIngestStatus(prev => ({ ...prev, [materialId]: { status: 'done' } }))
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ingest fehlgeschlagen'
      setIngestStatus(prev => ({ ...prev, [materialId]: { status: 'error', error: msg } }))
    }
  }

  async function handleIngestAll() {
    const notIndexed = materials.filter(m => !m.indexed)
    for (const m of notIndexed) {
      await handleIngest(m.id)
    }
  }

  async function handleDeleteMaterial(materialId: string) {
    if (!confirm('Material löschen?')) return
    try {
      await fetch(`${API}/api/materials/${materialId}`, { method: 'DELETE' })
      setMaterials(prev => prev.filter(m => m.id !== materialId))
    } catch {
      alert('Löschen fehlgeschlagen.')
    }
  }

  const hasPending = uploadQueue.some(i => i.status === 'pending')
  const notIndexed = materials.filter(m => !m.indexed)

  const surface = { backgroundColor: 'var(--surface)', border: '1px solid var(--border)' }
  const inputStyle = {
    backgroundColor: 'var(--surface-2)',
    border: '1px solid var(--border)',
    color: 'var(--text)',
    borderRadius: '6px',
    padding: '5px 10px',
    fontSize: '12px',
    outline: 'none',
  }

  return (
    <div className="min-h-[calc(100vh-3.5rem)] py-12">
      <div className="max-w-3xl mx-auto px-6">

        <Link
          href={`/courses/${courseId}`}
          className="inline-flex items-center gap-1.5 text-sm mb-8 transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7" />
          </svg>
          Zurück
        </Link>

        <h1 className="text-2xl font-semibold mb-10 tracking-tight" style={{ color: 'var(--text)' }}>
          Materialien
        </h1>

        {/* Upload Section */}
        <section className="mb-10">
          <div
            className="p-5 rounded-xl"
            style={surface}
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
                PDFs hochladen
              </h2>
              <div className="flex items-center gap-2">
                <label className="text-xs" style={{ color: 'var(--text-muted)' }}>Standard-Typ</label>
                <select
                  value={defaultType}
                  onChange={e => setDefaultType(e.target.value as MaterialType)}
                  style={inputStyle}
                >
                  {Object.entries(TYPE_LABELS).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Drop zone */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadQueue.length >= 20}
              className="w-full rounded-lg py-8 flex flex-col items-center gap-2 transition-all disabled:opacity-40 cursor-pointer"
              style={{
                border: '1px dashed var(--border-2)',
                backgroundColor: 'var(--surface-2)',
                color: 'var(--text-muted)',
              }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span className="text-xs">
                {uploadQueue.length >= 20
                  ? 'Maximum 20 Dateien erreicht'
                  : 'PDFs auswählen (max. 20)'}
              </span>
            </button>

            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              multiple
              className="hidden"
              onChange={handleFileSelect}
            />

            {/* Queue list */}
            {uploadQueue.length > 0 && (
              <div className="mt-4 space-y-2">
                {uploadQueue.map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg"
                    style={{ backgroundColor: 'var(--surface-2)' }}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-xs truncate" style={{ color: 'var(--text)' }}>
                        {item.file.name}
                      </p>
                      {item.error && (
                        <p className="text-xs text-red-400 mt-0.5">{item.error}</p>
                      )}
                    </div>

                    {item.status === 'pending' && (
                      <select
                        value={item.type}
                        onChange={e => updateQueueType(i, e.target.value as MaterialType)}
                        style={{ ...inputStyle, width: 'auto' }}
                      >
                        {Object.entries(TYPE_LABELS).map(([v, l]) => (
                          <option key={v} value={v}>{l}</option>
                        ))}
                      </select>
                    )}

                    <StatusBadge status={item.status} />

                    {item.status !== 'uploading' && (
                      <button
                        onClick={() => removeFromQueue(i)}
                        className="p-1 rounded transition-colors"
                        style={{ color: 'var(--text-dim)' }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="18" y1="6" x2="6" y2="18" />
                          <line x1="6" y1="6" x2="18" y2="18" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Action buttons */}
            {uploadQueue.length > 0 && (
              <div className="mt-4 flex gap-2">
                <button
                  onClick={handleUpload}
                  disabled={uploading || !hasPending}
                  className="flex-1 py-2 rounded-lg text-sm font-medium transition-all disabled:opacity-40"
                  style={{ backgroundColor: 'var(--accent)', color: '#000' }}
                >
                  {uploading ? 'Wird hochgeladen…' : `${uploadQueue.filter(i => i.status === 'pending').length} PDF${uploadQueue.filter(i => i.status === 'pending').length !== 1 ? 's' : ''} hochladen`}
                </button>
                {uploadQueue.some(i => i.status === 'done') && (
                  <button
                    onClick={clearDoneFromQueue}
                    className="px-4 py-2 rounded-lg text-xs transition-all"
                    style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
                  >
                    Erledigte entfernen
                  </button>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Materials list */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>
              Hochgeladene Materialien
              {materials.length > 0 && (
                <span className="ml-2 text-xs font-normal" style={{ color: 'var(--text-muted)' }}>
                  ({materials.length})
                </span>
              )}
            </h2>
            {notIndexed.length > 0 && (
              <button
                onClick={handleIngestAll}
                className="text-xs px-3 py-1.5 rounded-lg transition-all"
                style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
              >
                Alle {notIndexed.length} ingesten
              </button>
            )}
          </div>

          {loadingMaterials ? (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Lädt…</p>
          ) : materials.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Noch keine Materialien hochgeladen.
            </p>
          ) : (
            <div className="space-y-2">
              {materials.map(material => {
                const entry = ingestStatus[material.id] ?? { status: 'idle' }
                const status = entry.status
                return (
                  <div
                    key={material.id}
                    className="flex items-start gap-4 px-4 py-3 rounded-xl"
                    style={surface}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate" style={{ color: 'var(--text)' }}>
                        {material.title}
                      </p>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        {TYPE_LABELS[material.type]}
                        {material.page_count != null && ` · ${material.page_count} Seiten`}
                      </p>
                      {status === 'error' && entry.error && (
                        <p className="text-xs mt-1" style={{ color: '#f87171' }}>{entry.error}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {material.parse_status === 'pending' && (
                        <span className="text-xs flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}>
                          <svg className="animate-spin" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                          </svg>
                          Verarbeitung…
                        </span>
                      )}
                      {material.parse_status === 'error' && (
                        <span className="text-xs" style={{ color: '#f87171' }}>Extraktion fehlgeschlagen</span>
                      )}
                      {material.indexed ? (
                        <span
                          className="text-xs px-2 py-0.5 rounded-md"
                          style={{ backgroundColor: 'rgba(34,197,94,0.1)', color: '#4ade80', border: '1px solid rgba(34,197,94,0.2)' }}
                        >
                          indexiert
                        </span>
                      ) : (
                        <button
                          onClick={() => handleIngest(material.id)}
                          disabled={status === 'running' || material.parse_status !== 'done'}
                          className="text-xs px-3 py-1 rounded-lg transition-all disabled:opacity-40"
                          style={{ backgroundColor: 'var(--surface-2)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
                        >
                          {status === 'running' ? 'Ingestiert…' : status === 'error' ? 'Nochmal' : 'Ingesten'}
                        </button>
                      )}

                      <button
                        onClick={() => handleDeleteMaterial(material.id)}
                        className="p-1.5 rounded-md transition-colors"
                        style={{ color: 'var(--text-dim)' }}
                        title="Material löschen"
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                          <path d="M10 11v6M14 11v6" />
                          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                        </svg>
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </section>

      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: UploadItem['status'] }) {
  if (status === 'pending') return null
  if (status === 'uploading') return (
    <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  )
  if (status === 'done') return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  )
}
