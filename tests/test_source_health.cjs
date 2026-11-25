const test = require('node:test');
const assert = require('node:assert/strict');
const { report, outcomes } = require('../scripts/ci/source-health.cjs');
const log = (failed = 1, discovered = 10) => `🔍 IMPORT: EPISODI\n✅ Löydettiin ${discovered} arvostelua\n❌ Epäonnistui: ${failed}\n❌ Source failures: {'episodi': ${failed}}`;
async function run(text, previous, runId = 4) {
  const calls = [], warnings = [], failures = [];
  const core = { warning: s => warnings.push(s), setFailed: s => failures.push(s), summary: { addHeading() { return this; }, addRaw() { return this; }, async write() {} } };
  const github = { paginate: async () => previous ? [{ number: 8, title: 'Scraper source health', body: `<!-- source-health: ${JSON.stringify(previous)} -->` }] : [], rest: { issues: { listForRepo() {}, update: async o => calls.push(o), create: async o => calls.push(o) } } };
  await report({ github, core, context: { repo: { owner: 'test', repo: 'test' }, serverUrl: 'https://github.com', runId }, log: text });
  return { calls, warnings, failures };
}
test('isolated item warns without red, creates one health issue', async () => {
  const r = await run(log()); assert.equal(r.failures.length, 0); assert.equal(r.warnings.length, 1); assert.equal(r.calls.length, 1);
});
test('same issue updated; third consecutive failure is red', async () => {
  const r = await run(log(), { episodi: { count: 2, run: '3' } }); assert.equal(r.failures.length, 1); assert.equal(r.calls[0].issue_number, 8);
});
test('rerun does not increment streak', async () => {
  const r = await run(log(), { episodi: { count: 2, run: '4' } }); assert.equal(r.failures.length, 0); assert.match(r.calls[0].body, /streak 2/);
});
test('healthy batch clears streak and closes issue', async () => {
  const r = await run(log(0).split("❌ Source failures:")[0], { episodi: { count: 2, run: '3' } }); assert.equal(r.calls[0].state, 'closed'); assert.match(r.calls[0].body, /source-health: {}/);
});
test('source-wide article loss is red even first time', async () => { assert.equal((await run(log(10))).failures.length, 1); });
test('discovery failure is source-wide', async () => { assert.equal((await run('🔍 IMPORT: TS\nDiscovery failed for ts: unavailable')).failures.length, 1); });
test('unclassified final failure is not silently green', async () => { await assert.rejects(run('Source failures: unknown'), /could not be classified/); });
test('real batch fixture has two isolated failures', () => { const r = outcomes(log() + '\n🔍 IMPORT: MUROPAKETTI\nLöydettiin 10 arvostelua\nEpäonnistui: 1'); assert.equal(r.episodi.whole, false); assert.equal(r.muropaketti.failed, 1); });
