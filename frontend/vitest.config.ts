import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [],
    exclude: ['node_modules', 'tests-e2e/**'],
    server: {
      deps: {
        // react-markdown v10+ and related unified/remark/rehype packages are ESM-only;
        // inline them so Vite transforms them for the jsdom test environment.
        inline: [
          /react-markdown/,
          /unified/,
          /remark-math/,
          /rehype-katex/,
          /remark-parse/,
          /remark-rehype/,
          /rehype-stringify/,
          /mdast-util-math/,
          /hast-util-to-jsx-runtime/,
          /bail/,
          /is-plain-obj/,
          /trough/,
          /vfile/,
          /micromark/,
          /mdast-util/,
          /hast-util/,
          /unist-util/,
          /property-information/,
          /space-separated-tokens/,
          /comma-separated-tokens/,
          /decode-named-character-reference/,
          /character-entities/,
          /hastscript/,
          /web-namespaces/,
          /devlop/,
        ],
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
    },
  },
})
