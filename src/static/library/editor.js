document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#library-form");
  const editorNode = document.querySelector("#note-editor");
  const kind = document.querySelector("#id_kind");
  if (!form || !editorNode || !window.Quill) return;
  const quill = new Quill(editorNode, {
    theme: "snow",
    modules: {toolbar: [[{header:[1,2,3,false]}],["bold","italic","underline","strike"],[{list:"ordered"},{list:"bullet"}], ["blockquote","code-block","link"],["clean"]]}
  });
  const deltaInput = document.querySelector("#id_note_delta_json");
  const htmlInput = document.querySelector("#id_note_html_input");
  const textInput = document.querySelector("#id_note_text_input");
  try { const initial = JSON.parse(deltaInput.value || "{}"); if (initial.ops) quill.setContents(initial); } catch (_) {}
  function toggle() { document.querySelector("#note-editor-wrap").hidden = kind.value !== "note"; }
  kind.addEventListener("change", toggle); toggle();
  form.addEventListener("submit", () => {
    deltaInput.value = JSON.stringify(quill.getContents());
    htmlInput.value = quill.getSemanticHTML();
    textInput.value = quill.getText().trim();
  });
});

