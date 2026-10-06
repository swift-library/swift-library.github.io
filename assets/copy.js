"use strict";

if (navigator.clipboard && window.isSecureContext) {
  document.querySelectorAll(".project-install-area").forEach((area) => {
    const button = area.querySelector(".copy-button");
    const code = area.querySelector("code");
    const status = area.querySelector(".copy-status");
    if (!button || !code || !status) return;
    button.hidden = false;
    let reset;
    button.addEventListener("click", async () => {
      clearTimeout(reset);
      status.textContent = "";
      button.disabled = true;
      try {
        await navigator.clipboard.writeText(code.textContent);
        button.textContent = "Copied";
        status.textContent = "Installation command copied.";
      } catch {
        button.textContent = "Retry";
        status.textContent = "Copy failed. Select the command and copy it manually.";
      } finally {
        button.disabled = false;
        reset = setTimeout(() => { button.textContent = "Copy"; }, 2400);
      }
    });
  });
}
