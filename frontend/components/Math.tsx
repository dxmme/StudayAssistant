import katex from 'katex'

export function Math({ tex }: { tex: string }) {
  const html = katex.renderToString(tex, { throwOnError: false })
  return (
    <div className="katex-container" dangerouslySetInnerHTML={{ __html: html }} />
  )
}
