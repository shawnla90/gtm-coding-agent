// One-shot funnel + manual-review queue. Read-only.
const { DatabaseSync } = require('node:sqlite');
const path = require('path');
const db = new DatabaseSync(path.join(__dirname, 'li_outreach.db'));
const c = (q) => db.prepare(q).get().n;

console.log(JSON.stringify({
  sourced: c('SELECT COUNT(*) n FROM leads'),
  cr_sent: c('SELECT COUNT(*) n FROM leads WHERE cr_sent_at IS NOT NULL'),
  accepted: c('SELECT COUNT(*) n FROM leads WHERE accepted_at IS NOT NULL'),
  msg1_sent: c(`SELECT COUNT(*) n FROM leads WHERE msg1_status='sent'`),
  replied: c(`SELECT COUNT(*) n FROM leads WHERE reply_status='replied'`),
  queued: c(`SELECT COUNT(*) n FROM leads WHERE cr_status='pending' AND accepted_at IS NULL`),
}, null, 2));

// Rows stranded mid-send by a crash — verify each on LinkedIn BY HAND before resolving.
const stuck = db.prepare(
  `SELECT profile_url, first_name, cr_status, msg1_status, last_error, updated_at
   FROM leads WHERE cr_status='sending' OR msg1_status='sending'`
).all();
if (stuck.length) {
  console.log('\nSTUCK IN SENDING — review by hand, then resolve to sent or pending:');
  for (const r of stuck) console.log(` ${r.first_name} | cr=${r.cr_status} msg1=${r.msg1_status} | ${r.profile_url} (${r.updated_at})`);
} else {
  console.log('\nno rows stuck in sending.');
}
