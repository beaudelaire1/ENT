document.addEventListener("DOMContentLoaded", () => {
  const grid = document.querySelector("#dashboard-grid");
  if (!grid) return;
  let dragged = null;
  grid.querySelectorAll("[data-widget]").forEach((card) => {
    card.addEventListener("dragstart", () => { dragged = card; card.classList.add("dragging"); });
    card.addEventListener("dragend", () => { card.classList.remove("dragging"); dragged = null; save(); });
    card.addEventListener("dragover", (event) => {
      event.preventDefault();
      if (dragged && dragged !== card) {
        const rect = card.getBoundingClientRect();
        grid.insertBefore(dragged, event.clientY < rect.top + rect.height / 2 ? card : card.nextSibling);
      }
    });
  });
  grid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-move-widget]");
    if (!button) return;
    const card = button.closest("[data-widget]");
    if (button.dataset.moveWidget === "up" && card.previousElementSibling) grid.insertBefore(card, card.previousElementSibling);
    if (button.dataset.moveWidget === "down" && card.nextElementSibling) grid.insertBefore(card.nextElementSibling, card);
    save().then(() => {
      const status = document.querySelector("#layout-status");
      if (status) status.textContent = `${card.querySelector("h2")?.textContent || "Widget"} déplacé.`;
      button.focus();
    });
  });
  async function save() {
    const token = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "";
    await fetch(grid.dataset.layoutUrl, {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": token},
      body: JSON.stringify({widgets: [...grid.querySelectorAll("[data-widget]")].map(el => ({kind: el.dataset.widget, visible: true}))})
    });
  }
  document.querySelector("[data-save-widgets]")?.addEventListener("click", async () => {
    const token = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "";
    const response = await fetch(grid.dataset.layoutUrl, {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CSRFToken": token},
      body: JSON.stringify({widgets: [...document.querySelectorAll("[data-widget-toggle]")].map(input => ({kind: input.dataset.widgetToggle, visible: input.checked}))})
    });
    if (response.ok) window.location.reload();
  });
});
