document.addEventListener("DOMContentLoaded", () => {
  const button = document.querySelector("[data-toggle-sidebar]");
  const sidebar = document.querySelector(".sidebar");
  button?.addEventListener("click", () => sidebar?.classList.toggle("open"));
});

