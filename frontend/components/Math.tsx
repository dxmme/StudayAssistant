import katex from 'katex'

export function Math({ tex, display = true }: { tex: string; display?: boolean }) {
  const html = katex.renderToString(tex, { throwOnError: false, displayMode: display })
  return (
    <div className="katex-container" dangerouslySetInnerHTML={{ __html: html }} />
  )
}
