import { resolve } from 'node:path'
import { defineConfig } from 'vitest/config'
import base from '../../../../web/vite.config'
const here = new URL('.', import.meta.url).pathname
export default defineConfig({ ...base, root: resolve(here, '../../../../web'), test: { ...base.test, include: [resolve(here, 'approval-async.test.tsx')], exclude: [] } })
