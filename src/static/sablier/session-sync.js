/* Une entrée par session évite que deux onglets écrasent leurs files respectives. */
(() => {
  function create({owner, url, csrf, notify = () => {}, storage, send = (...args) => fetch(...args)}) {
    const prefix = `myent:sablier:pending:${owner}:`;
    const memory = new Map();
    let busy = false;
    try { storage ??= globalThis.localStorage; } catch (_) { storage = null; }
    function pending() {
      const entries = new Map(memory);
      try {
        for (let i = 0; i < storage.length; i++) {
          const key = storage.key(i);
          if (key?.startsWith(prefix)) entries.set(key, JSON.parse(storage.getItem(key)));
        }
      } catch (_) { /* La copie en mémoire reste disponible si le stockage est refusé. */ }
      return entries;
    }
    function enqueue(payload) {
      const key = prefix + payload.session_id;
      memory.set(key, payload);
      try {
        storage.setItem(key, JSON.stringify(payload));
        notify("Session en attente de synchronisation.");
      } catch (_) {
        notify("Stockage indisponible : gardez cette page ouverte jusqu’à l’enregistrement de la session.");
      }
    }
    async function flush() {
      if (busy) return;
      busy = true;
      let failed = false, saved = false;
      try {
        for (const [key, payload] of pending()) {
          try {
            const response = await send(url, {
              method: "POST", credentials: "same-origin", redirect: "error",
              headers: {"Content-Type": "application/json", "X-CSRFToken": csrf()},
              body: JSON.stringify(payload), signal: AbortSignal.timeout(15000),
            });
            if (response.status === 401 || response.status === 403) {
              notify("Session conservée : reconnectez-vous au même compte puis réessayez.");
              failed = true;
              break;
            }
            const receipt = response.ok ? await response.json() : null;
            if (!response.ok || receipt?.ok !== true || String(receipt.owner) !== String(owner) || receipt.session_id !== payload.session_id) {
              notify("Session non enregistrée, conservée pour réessayer. Vérifiez le compte et la compétence sélectionnés.");
              failed = true;
              continue;
            }
            // Effacer uniquement après un reçu correspondant à ce compte et cette session.
            try { storage.removeItem(key); } catch (_) { /* Un renvoi restera idempotent. */ }
            memory.delete(key);
            saved = true;
          } catch (_) {
            failed = true;
            notify("Session en attente de synchronisation. Nouvel essai au retour de la connexion.");
            break;
          }
        }
        if (saved && !failed) notify("Sessions enregistrées.");
      } finally { busy = false; }
    }
    return {enqueue, flush, pending};
  }
  globalThis.SablierSessionSync = {create};
  if (typeof module !== "undefined") module.exports = {create};
})();
