/**
 * Concurrent scenario initialisation must not race the backend.
 *
 * Two consumers (React StrictMode, two components, a retry) calling the
 * initialiser at the same time must produce ONE destructive reset, ONE
 * propose, no 409s, and the same resolved snapshot for both.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import snapshots from './__fixtures__/backend-snapshots.json';
import { replayDemo } from './backendAdapter';
import { _resetReplayForTests, replayOnce } from './scenarioSource';

type Call = { method: string; path: string; body?: Record<string, unknown> };

/** A deterministic fake backend that enforces the real state machine's key rule:
 *  `propose` is only legal once after a reset (a second one is a 409). */
function fakeBackend() {
  const calls: Call[] = [];
  let state = 'FORECASTED';
  const applied = new Set<string>();
  let scenarioReads = 0;
  const bundles = [snapshots.initial, snapshots.corrected, snapshots.closed];

  const fetchImpl = async (input: string | URL, init?: RequestInit): Promise<Response> => {
    const path = String(input);
    const method = init?.method ?? 'GET';
    const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
    calls.push({ method, path, body });
    const json = (status: number, data: unknown) => new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });

    if (path === '/api/demo/reset') {
      state = 'FORECASTED';
      applied.clear();
      scenarioReads = 0;
      return json(200, { id: 'case-bhatpar-amox-001', state });
    }
    if (path === '/api/demo/scenario') {
      const b = bundles[Math.min(scenarioReads, 2)];
      scenarioReads += 1;
      return json(200, b);
    }
    if (path.endsWith('/advance')) {
      const cmd = String(body?.command_id ?? '');
      if (cmd && applied.has(cmd)) return json(200, { id: 'case-bhatpar-amox-001', state });   // idempotent replay
      if (body?.action === 'propose') {
        if (state !== 'FORECASTED') return json(409, { code: 'illegal_transition', message: `propose not legal in ${state}` });
        state = 'INTERVENTION_PROPOSED';
      } else {
        state = String(body?.action).toUpperCase();
      }
      if (cmd) applied.add(cmd);
      return json(200, { id: 'case-bhatpar-amox-001', state });
    }
    if (path.endsWith('/evidence')) return json(201, { id: 'ev-001', state: 'awaiting_confirmation' });
    if (path.includes('/evidence/') && path.endsWith('/confirm')) return json(200, { id: 'case-bhatpar-amox-001', state: 'PLAN_RECALCULATED' });
    return json(404, { code: 'not_found', message: path });
  };

  return { calls, fetchImpl, count: (pred: (c: Call) => boolean) => calls.filter(pred).length };
}

describe('concurrent scenario initialisation', () => {
  let fb: ReturnType<typeof fakeBackend>;

  beforeEach(() => {
    _resetReplayForTests();
    fb = fakeBackend();
    vi.stubGlobal('fetch', vi.fn(fb.fetchImpl));
  });
  afterEach(() => vi.unstubAllGlobals());

  it('two concurrent initialisations share one replay: one reset, one propose, no 409, identical result', async () => {
    const [a, b] = await Promise.all([replayOnce(), replayOnce()]);
    expect(a).toBe(b);                                                                   // same promise result object
    expect(fb.count((c) => c.path === '/api/demo/reset')).toBe(1);
    expect(fb.count((c) => c.body?.action === 'propose')).toBe(1);
    expect(fb.calls.every((c) => c.path !== '/api/demo/reset' || c.method === 'POST')).toBe(true);
    expect(a.initial.forecasts.bhatpar.coverage_breach_day).toBe(8);
    expect(a.closed.case.care_protected_count).toBe(13);
  });

  it('a later consumer after completion still gets the same snapshots without a second replay', async () => {
    const first = await replayOnce();
    const again = await replayOnce();
    expect(again).toBe(first);
    expect(fb.count((c) => c.path === '/api/demo/reset')).toBe(1);
  });

  it('WITHOUT the dedupe, two raw replays do race and the backend rejects the duplicate propose', async () => {
    await expect(Promise.all([replayDemo(), replayDemo()])).rejects.toThrow(/409/);
    expect(fb.count((c) => c.path === '/api/demo/reset')).toBeGreaterThanOrEqual(2);
  });

  it('every command carries a run-scoped command_id so backend idempotency can absorb retries', async () => {
    await replayOnce();
    const advances = fb.calls.filter((c) => c.path.endsWith('/advance'));
    expect(advances.length).toBeGreaterThan(5);
    const ids = advances.map((c) => String(c.body?.command_id));
    expect(ids.every((id) => /^replay-[a-z0-9]+-[a-z0-9]+:[a-z_]+$/.test(id))).toBe(true);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('a failed replay clears the in-flight slot so a retry can succeed', async () => {
    let fail = true;
    vi.stubGlobal('fetch', vi.fn(async (input: string | URL, init?: RequestInit) => {
      if (fail && String(input) === '/api/demo/reset') return new Response('down', { status: 503 });
      return fb.fetchImpl(input, init);
    }));
    await expect(replayOnce()).rejects.toThrow(/503/);
    fail = false;
    const ok = await replayOnce();
    expect(ok.initial.case.id).toBe('case-bhatpar-amox-001');
  });
});
