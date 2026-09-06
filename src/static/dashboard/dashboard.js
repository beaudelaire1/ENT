document.addEventListener("DOMContentLoaded", () => {
  const grid = document.querySelector("#dashboard-grid");
  if (!grid) return;
  const status = document.querySelector("#layout-status");
  let dragged = null, saves = Promise.resolve();
  function announce(message) { if (status) status.textContent = message; }
  function layout(applyVisibility = false) {
    const toggles = [...document.querySelectorAll("[data-widget-toggle]")];
    const visible = [...grid.querySelectorAll("[data-widget]")].map(el => el.dataset.widget);
    const order = [...visible, ...toggles.map(el => el.dataset.widgetToggle).filter(kind => !visible.includes(kind))];
    return order.map(kind => ({kind, visible: applyVisibility ? toggles.find(el => el.dataset.widgetToggle === kind).checked : visible.includes(kind)}));
  }
  function save(widgets = layout()) {
    announce("Enregistrement en cours…");
    // Les réponses ne doivent pas inverser l'ordre de deux déplacements rapides.
    saves = saves.then(async () => {
      try {
        const response = await fetch(grid.dataset.layoutUrl, {
          method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": document.cookie.match(/csrftoken=([^;]+)/)?.[1] || ""},
          body: JSON.stringify({widgets}), redirect: "error",
        });
        if (!response.ok) throw new Error("save failed");
        announce("Disposition enregistrée.");
        return true;
      } catch (_) {
        announce("Disposition non enregistrée. Vérifiez la connexion puis réessayez avec Appliquer.");
        return false;
      }
    });
    return saves;
  }
  grid.querySelectorAll("[data-widget]").forEach(card => {
    card.addEventListener("dragstart", () => { dragged = card; card.classList.add("dragging"); });
    card.addEventListener("dragend", () => { card.classList.remove("dragging"); dragged = null; save(); });
    card.addEventListener("dragover", event => {
      event.preventDefault();
      if (dragged && dragged !== card) {
        const rect = card.getBoundingClientRect();
        grid.insertBefore(dragged, event.clientY < rect.top + rect.height / 2 ? card : card.nextSibling);
      }
    });
  });
  grid.addEventListener("click", event => {
    const button = event.target.closest("[data-move-widget]");
    if (!button) return;
    const card = button.closest("[data-widget]");
    if (button.dataset.moveWidget === "up" && card.previousElementSibling) grid.insertBefore(card, card.previousElementSibling);
    if (button.dataset.moveWidget === "down" && card.nextElementSibling) grid.insertBefore(card.nextElementSibling, card);
    save().then(() => button.focus());
  });
  document.querySelector("[data-save-widgets]")?.addEventListener("click", async event => {
    const button = event.currentTarget;
    button.disabled = true;
    if (await save(layout(true))) window.location.reload();
    else button.disabled = false;
  });
});
