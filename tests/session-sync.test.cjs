const {test} = require('node:test');
const assert = require('node:assert/strict');
const {create} = require('../src/static/sablier/session-sync.js');
const clock = require('../src/static/sablier/session-clock.js');
function storage() {
  const rows = new Map();
  return {get length() {return rows.size;}, key: i => [...rows.keys()][i], getItem: k => rows.get(k), setItem: (k,v) => rows.set(k,v), removeItem: k => rows.delete(k)};
}
const payload = {session_id: 'unique-session', owner: '1', seconds: 60};
const receipt = p => ({status: 200, ok: true, json: async () => ({ok: true, owner: p.owner, session_id: p.session_id})});

test('une session reste durable après panne puis recharge', async () => {
  const store = storage();
  const a = create({owner: '1', storage: store, csrf: () => '', send: async () => {throw Error('offline');}});
  a.enqueue(payload); await a.flush(); assert.equal(store.length, 1);
  const b = create({owner: '1', storage: store, csrf: () => '', send: async () => receipt(payload)});
  await b.flush(); assert.equal(store.length, 0);
});
test('deux onglets gardent toutes les entrées et les comptes sont isolés', async () => {
  const store = storage();
  const options = {owner: '1', storage: store, csrf: () => '', send: async (_url, req) => receipt(JSON.parse(req.body))};
  const a = create(options), b = create(options);
  a.enqueue(payload); b.enqueue({...payload, session_id: 'second'});
  const other = create({...options, owner: '2'});
  assert.equal(other.pending().size, 0);
  await b.flush(); assert.equal(store.length, 0);
});
test('un refus de compte ou un faux reçu ne supprime pas la session', async () => {
  for (const response of [{status: 403}, receipt({...payload, owner: '2'}), receipt({...payload, session_id: 'other'})]) {
    const store = storage();
    const queue = create({owner: '1', storage: store, csrf: () => '', send: async () => response});
    queue.enqueue(payload); await queue.flush(); assert.equal(store.length, 1);
  }
});
test('pauses et changements du compte à rebours ne gonflent pas le temps actif', () => {
  const state = {};
  clock.begin(state, 0, 'id', '4'); state.running = true; state.endsAt = 60000;
  clock.accrue(state, 20000); state.running = false;
  clock.begin(state, 80000, 'ignored', '4'); state.running = true; state.endsAt = 120000;
  const result = clock.payload(state, '1', 130000);
  assert.equal(result.seconds, 60); assert.equal(result.session_id, 'id');
  assert.equal(result.started_at, '1970-01-01T00:00:00.000Z');
  assert.equal(result.ended_at, '1970-01-01T00:02:00.000Z');
});
