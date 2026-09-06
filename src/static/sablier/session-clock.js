/* Horodatage indépendant du rendu : les pauses ne sont pas du temps travaillé. */
(() => {
  function begin(state, now, id, competency) {
    if (!state.sessionId) {
      state.sessionId = id;
      state.startedAt = now;
      state.activeSeconds = 0;
      state.competency = competency || null;
    }
    state.activeStartedAt = now;
  }
  function accrue(state, now) {
    if (state.running && state.activeStartedAt != null) {
      state.activeSeconds = (state.activeSeconds || 0) + Math.max(0, Math.min(now, state.endsAt) - state.activeStartedAt) / 1000;
      state.activeStartedAt = now;
    }
  }
  function clear(state) {
    for (const key of ["sessionId", "startedAt", "activeStartedAt", "activeSeconds", "queued", "competency"]) delete state[key];
  }
  function payload(state, owner, now) {
    const ended = state.running ? Math.min(now, state.endsAt) : now;
    accrue(state, now);
    const seconds = Math.min(86400, Math.round(state.activeSeconds || 0));
    if (!state.sessionId || seconds < 1) return null;
    return {
      session_id: state.sessionId, owner, seconds,
      started_at: new Date(state.startedAt).toISOString(), ended_at: new Date(ended).toISOString(),
      intention: state.intention || "", competency: state.competency || null,
    };
  }
  globalThis.SablierSessionClock = {begin, accrue, clear, payload};
  if (typeof module !== "undefined") module.exports = globalThis.SablierSessionClock;
})();
