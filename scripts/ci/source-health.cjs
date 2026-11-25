// Isolated item failures warn; source-wide or three consecutive degraded
// batches fail the health gate after validated publication. State is stored
// in one issue, not in the review database or a second data commit.
const title = 'Scraper source health';
const marker = /<!-- source-health: (.*?) -->/;
function outcomes(log) {
  const result = {};
  let source;
  for (const line of log.split('\n')) {
    const start = line.match(/🔍 IMPORT: ([A-Z]+)/);
    if (start) { source = start[1].toLowerCase(); result[source] = { failed: 0, discovered: null, whole: false }; }
    if (!source) continue;
    const row = result[source];
    const count = line.match(/Löydettiin (\d+) arvostelua/);
    if (count) row.discovered = Number(count[1]);
    const failed = line.match(/Epäonnistui:\s*(\d+)/);
    if (failed) row.failed = Number(failed[1]);
    if (/Discovery failed for |Ei scraperia lähteelle:|Julkaisua ei löydy tietokannasta:/.test(line)) {
      row.failed = Math.max(1, row.failed); row.whole = true;
    }
  }
  // The final map also includes failures carried by a persistent queue.
  const final = log.match(/Source failures: (\{[^\n]+\})/);
  if (final) for (const entry of final[1].matchAll(/'([a-z]+)': (\d+)/g)) {
    result[entry[1]] ??= { discovered: null, whole: false, failed: 0 };
    result[entry[1]].failed = Number(entry[2]);
  }
  for (const row of Object.values(result)) {
    row.whole ||= row.discovered > 0 && row.failed >= row.discovered;
  }
  return result;
}
async function report({ github, context, core, log }) {
  const rows = outcomes(log);
  // Do not silently turn an unclassifiable partial scrape green.
  if (/Source failures:/.test(log) && !Object.values(rows).some(r => r.failed)) {
    throw new Error('Source failures could not be classified; inspect batch log');
  }
  const issues = await github.paginate(github.rest.issues.listForRepo, { ...context.repo, state: 'all', per_page: 100 });
  const issue = issues.find(i => !i.pull_request && i.title === title);
  let previous = {};
  if (issue && marker.test(issue.body || '')) {
    try { previous = JSON.parse(issue.body.match(marker)[1]); }
    catch { throw new Error('Invalid source-health state in issue'); }
  }
  for (const row of Object.values(previous)) {
    if (!row || !Number.isSafeInteger(row.count) || row.count < 1 || typeof row.run !== 'string') throw new Error('Invalid source-health counters');
  }
  const streaks = {};
  const failed = Object.entries(rows).filter(([, r]) => r.failed);
  const severe = [];
  for (const [source, row] of failed) {
    // A rerun of the same batch is not another consecutive failure.
    const old = previous[source];
    const count = old?.run === String(context.runId) ? old.count : (old?.count || 0) + 1;
    streaks[source] = { count, run: String(context.runId) };
    core.warning(`${source}: ${row.failed} item(s) failed, consecutive degraded batches: ${count}`);
    if (row.whole || count >= 3) severe.push(source);
  }
  const run = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const body = [
    'Source health after validated publication. Isolated items warn; source-wide loss or 3 consecutive degraded batches fail the health gate.',
    '', `Latest batch: ${run}`, '',
    ...failed.map(([s, r]) => `- ${s}: ${r.failed} failure(s), ${r.discovered ?? 'unknown'} discovered, streak ${streaks[s].count}${r.whole ? ', source-wide' : ''}. See per-item batch log.`),
    failed.length ? '' : 'All sources healthy in the latest batch.',
    '', `<!-- source-health: ${JSON.stringify(streaks)} -->`,
  ].join('\n');
  if (issue) await github.rest.issues.update({ ...context.repo, issue_number: issue.number, body, state: failed.length ? 'open' : 'closed' });
  else if (failed.length) await github.rest.issues.create({ ...context.repo, title, body });
  await core.summary.addHeading('Source health').addRaw(body.split('<!--')[0]).write();
  if (severe.length) core.setFailed(`Sustained or source-wide loss: ${severe.join(', ')}. Valid imports were published.`);
}
module.exports = { outcomes, report };
