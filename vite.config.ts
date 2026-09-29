import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Build-time environment integrity.
 *
 * `resolvePolicy` throws when a staging/judge/production build is configured
 * to use the local synthetic seed, so such a build cannot be produced at all —
 * the same rule the runtime enforces. The policy module has no dependencies so
 * it is safe to import here.
 */
export default defineConfig(async ({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');
  const { resolvePolicy } = await import('./src/data/scenarioPolicy');
  const { resolveWorkspaceSource } = await import('./src/app/workspaceSource');
  const policy = resolvePolicy(env.VITE_APP_ENV, env.VITE_SCENARIO_SOURCE, env.VITE_HAVENGRID_MODE);
  resolveWorkspaceSource(env.VITE_WORKSPACE_SOURCE, env.VITE_APP_ENV, env.VITE_HAVENGRID_MODE);
  return {
    plugins: [react()],
    define: { __HAVENGRID_POLICY__: JSON.stringify(policy) },
    server: {
      port: 5173,
      open: false,
      // Only used when VITE_SCENARIO_SOURCE=backend
      proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
    },
    test: {
      environment: 'node',
      include: ['src/**/*.test.ts'],
    },
  };
});
