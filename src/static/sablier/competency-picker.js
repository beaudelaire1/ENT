/* La matière d'abord, puis ses compétences : une liste entière de formation ne se parcourt pas. */
(() => {
  const subject = document.getElementById("session-subject");
  const competency = document.getElementById("session-competency");
  if (!subject || !competency) { globalThis.SablierCompetencyPicker = {select() {}}; return; }

  const placeholder = competency.querySelector("option[value='']");
  // Tous les groupes sont rendus par le serveur ; seul celui de la matière choisie reste dans la liste.
  // Retirer le groupe plutôt que le masquer : Safari ignore `hidden` sur une option.
  const groups = [...competency.querySelectorAll("optgroup[data-subject]")];
  const holds = (group, id) => [...group.children].some((option) => option.value === String(id));

  function show(key, value) {
    for (const group of groups) group.remove();
    const group = groups.find((candidate) => candidate.dataset.subject === key);
    if (group) competency.append(group);
    competency.disabled = !group;
    placeholder.textContent = group ? "Choisir une compétence" : "Choisissez d’abord une matière";
    competency.value = group && value && holds(group, value) ? String(value) : "";
  }

  // Une session reprise connaît sa compétence, pas la matière d'où elle a été choisie :
  // la matière affichée est gardée si elle la contient, sinon la première qui la contient.
  function select(id) {
    if (!id) return;
    const current = groups.find((group) => group.dataset.subject === subject.value);
    const group = current && holds(current, id) ? current : groups.find((candidate) => holds(candidate, id));
    if (!group) return;
    subject.value = group.dataset.subject;
    show(group.dataset.subject, id);
  }

  show(subject.value, competency.value);
  subject.addEventListener("change", () => {
    show(subject.value, null);
    // Changer de matière abandonne la compétence : `sablier.js` doit l'oublier aussi.
    competency.dispatchEvent(new Event("change"));
  });
  globalThis.SablierCompetencyPicker = {select};
})();
