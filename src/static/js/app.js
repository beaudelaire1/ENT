// Comportements communs à toutes les pages : volet latéral, garde-fou de sortie et
// rattachement des messages d'erreur à leur champ.
(function () {
  "use strict";

  /* ---------------------------------------------------------------- volet latéral */
  // Le volet s'ouvrait et ne se refermait qu'en recliquant le même bouton : sur
  // téléphone, il restait déployé par-dessus la page qu'on venait d'ouvrir, et le focus
  // partait se perdre derrière lui.
  function setupSidebar() {
    var toggle = document.querySelector("[data-toggle-sidebar]");
    var sidebar = document.querySelector(".sidebar");
    var closeButton = document.querySelector("[data-close-sidebar]");
    var backdrop = document.querySelector("[data-sidebar-backdrop]");
    var mobile = window.matchMedia("(max-width: 760px)");
    if (!toggle || !sidebar) return;

    function isOpen() {
      return sidebar.classList.contains("open");
    }

    function close(restoreFocus) {
      if (!isOpen()) return;
      sidebar.classList.remove("open");
      document.body.classList.remove("sidebar-open");
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Ouvrir le menu");
      if (mobile.matches) sidebar.setAttribute("aria-hidden", "true");
      if (restoreFocus) toggle.focus();
    }

    function open() {
      sidebar.classList.add("open");
      document.body.classList.add("sidebar-open");
      toggle.setAttribute("aria-expanded", "true");
      toggle.setAttribute("aria-label", "Fermer le menu");
      sidebar.removeAttribute("aria-hidden");
      var first = closeButton || sidebar.querySelector("nav a");
      if (first) first.focus();
    }

    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", sidebar.id || "sidebar");
    if (mobile.matches) sidebar.setAttribute("aria-hidden", "true");

    toggle.addEventListener("click", function () {
      if (isOpen()) close(true);
      else open();
    });
    if (closeButton) closeButton.addEventListener("click", function () { close(true); });
    if (backdrop) backdrop.addEventListener("click", function () { close(true); });

    // Naviguer ferme le volet : la page demandée doit être visible en arrivant.
    sidebar.addEventListener("click", function (event) {
      if (event.target.closest("a")) close(false);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") close(true);
      if (event.key !== "Tab" || !isOpen() || !mobile.matches) return;
      var focusable = Array.from(sidebar.querySelectorAll("a, button, summary, input, select, textarea, [tabindex]:not([tabindex='-1'])"))
        .filter(function (node) { return !node.disabled && node.offsetParent !== null; });
      if (!focusable.length) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });

    document.addEventListener("click", function (event) {
      if (!isOpen()) return;
      if (sidebar.contains(event.target) || toggle.contains(event.target)) return;
      close(false);
    });

    mobile.addEventListener("change", function (event) {
      close(false);
      if (event.matches) sidebar.setAttribute("aria-hidden", "true");
      else sidebar.removeAttribute("aria-hidden");
    });
  }

  /* --------------------------------------------------------- garde-fou de sortie */
  // Quitter un formulaire rempli sans l'enregistrer faisait perdre la saisie sans un mot.
  // Le garde-fou ne se déclenche qu'après une modification réelle, et jamais sur
  // « Annuler » : ce bouton exprime déjà l'intention de partir.
  function setupUnsavedGuard() {
    var forms = document.querySelectorAll("form[data-guard-unsaved]");
    if (!forms.length) return;
    var dirty = false;
    var leaving = false;

    forms.forEach(function (form) {
      form.addEventListener("input", function () {
        dirty = true;
      });
      form.addEventListener("change", function () {
        dirty = true;
      });
      form.addEventListener("submit", function () {
        leaving = true;
      });
    });

    document.addEventListener("click", function (event) {
      if (event.target.closest("[data-leave-unguarded]")) leaving = true;
    });

    window.addEventListener("beforeunload", function (event) {
      if (!dirty || leaving) return;
      event.preventDefault();
      // Les navigateurs imposent leur propre texte ; seule la valeur de retour compte.
      event.returnValue = "";
    });
  }

  /* ------------------------------------------------- erreurs annoncées aux champs */
  // Django relie déjà un champ à son texte d'aide. Il ne relie pas son message d'erreur :
  // un lecteur d'écran annonçait le libellé et l'aide, jamais la raison du refus. Le lien
  // manquant est ajouté ici, à partir de la structure de `core/_form_fields.html` — un
  // gabarit ne peut pas ajouter d'attribut à un widget déjà rendu.
  function describeErrors() {
    document.querySelectorAll(".field-invalid").forEach(function (wrapper) {
      var control = wrapper.querySelector("input, select, textarea");
      var errors = wrapper.querySelector(".errorlist");
      if (!control || !errors) return;
      if (!errors.id) errors.id = control.id + "_errors";
      var described = (control.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
      if (described.indexOf(errors.id) === -1) described.push(errors.id);
      control.setAttribute("aria-describedby", described.join(" "));
      control.setAttribute("aria-invalid", "true");
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupSidebar();
    setupUnsavedGuard();
    describeErrors();
  });
})();
