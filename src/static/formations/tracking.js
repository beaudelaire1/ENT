// Retour visuel immédiat dans la grille de suivi : la barre suit le sélecteur avant
// même l'enregistrement, et un rappel signale les modifications en attente.
(function () {
  "use strict";

  var form = document.querySelector(".tracking-form");
  if (!form) return;

  var hint = form.querySelector("[data-dirty-hint]");

  function paint(select) {
    var bar = form.querySelector('[data-progress-for="' + select.id + '"] .progress-fill');
    if (!bar) return;
    var level = parseInt(select.value, 10) || 0;
    bar.style.width = level * 25 + "%";
    bar.className = "progress-fill level-" + level;
  }

  form.addEventListener("change", function (event) {
    if (event.target.matches("[data-level-select]")) paint(event.target);
    if (hint) hint.hidden = false;
  });

  form.addEventListener("input", function () {
    if (hint) hint.hidden = false;
  });

  form.addEventListener("submit", function () {
    if (hint) hint.hidden = true;
  });
})();
