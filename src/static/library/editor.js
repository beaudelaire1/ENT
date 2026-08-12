document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#library-form");
  const editor = document.querySelector("#note-editor");
  const kind = document.querySelector("#id_kind");
  if (!form || !editor || !kind) return;

  const deltaInput = document.querySelector("#id_note_delta_json");
  const htmlInput = document.querySelector("#id_note_html_input");
  const textInput = document.querySelector("#id_note_text_input");
  const visibleByKind = {link: ["#id_url"], file: ["#id_file"], note: ["#note-editor-wrap"]};

  if (htmlInput.value) editor.innerHTML = htmlInput.value;
  else {
    try {
      const initial = JSON.parse(deltaInput.value || "{}");
      editor.textContent = (initial.ops || []).map((operation) => operation.insert || "").join("").trimEnd();
    } catch (_) {}
  }

  function toggleFields() {
    Object.entries(visibleByKind).forEach(([expectedKind, selectors]) => {
      selectors.forEach((selector) => {
        const node = document.querySelector(selector);
        const field = selector === "#note-editor-wrap" ? node : node?.closest(".field");
        if (field) field.hidden = kind.value !== expectedKind;
      });
    });
  }
  kind.addEventListener("change", toggleFields);
  toggleFields();

  document.querySelector(".note-toolbar")?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-editor-command]");
    if (!button) return;
    editor.focus();
    const command = button.dataset.editorCommand;
    if (command === "createLink") {
      const url = window.prompt("Adresse du lien (https://…)");
      if (!url || !/^https?:\/\//i.test(url)) return;
      document.execCommand(command, false, url);
    } else document.execCommand(command, false, null);
  });

  form.addEventListener("submit", () => {
    const text = editor.innerText.trim();
    htmlInput.value = editor.innerHTML;
    textInput.value = text;
    deltaInput.value = JSON.stringify({ops: [{insert: `${text}\n`}]});
  });
});
