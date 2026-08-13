// Sélection multiple des pistes : la case « Tout », le décompte, et l'état des boutons.
//
// Rien d'essentiel ne dépend de ce script. Sans lui, les cases restent cochables une par
// une et les boutons restent utilisables — le serveur refuse simplement une sélection
// vide, avec un message. Il n'apporte que le confort : tout cocher d'un geste, et voir
// combien de pistes sont retenues avant d'appuyer sur « Supprimer ».
(() => {
  const form = document.getElementById("bulk-form");
  if (!form) return;

  const all = document.getElementById("bulk-select-all");
  const count = document.getElementById("bulk-count");
  const items = () => [...form.querySelectorAll("[data-bulk-item]")];
  const picked = () => items().filter((box) => box.checked);
  const actions = () => [...form.querySelectorAll("button[name='action']")];

  function refresh() {
    const chosen = picked().length;
    const total = items().length;
    count.textContent =
      chosen === 0 ? "Aucune piste sélectionnée" : `${chosen} piste${chosen > 1 ? "s" : ""} sur ${total}`;
    // Désactivés plutôt que masqués : un bouton qui disparaît puis réapparaît fait sauter
    // la mise en page à chaque case cochée.
    actions().forEach((button) => {
      button.disabled = chosen === 0;
    });
    all.checked = chosen > 0 && chosen === total;
    // L'état indéterminé distingue « quelques-unes » de « aucune », que la seule case
    // décochée confondrait.
    all.indeterminate = chosen > 0 && chosen < total;
  }

  all.addEventListener("change", () => {
    items().forEach((box) => {
      box.checked = all.checked;
    });
    refresh();
  });

  form.addEventListener("change", (event) => {
    if (event.target.matches("[data-bulk-item]")) refresh();
  });

  // Une suppression groupée passe par un écran de confirmation côté serveur ; ce rappel
  // ne le remplace pas, il évite l'aller-retour quand le clic était une erreur.
  form.addEventListener("submit", (event) => {
    const button = event.submitter;
    if (button && button.value === "delete" && picked().length === 0) event.preventDefault();
  });

  refresh();
})();
