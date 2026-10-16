const motion = window.matchMedia("(prefers-reduced-motion: reduce)");

function stills() {
  if (!motion.matches) return;
  for (const image of document.querySelectorAll("img[data-still]")) {
    image.src = image.dataset.still;
  }
}

stills();
motion.addEventListener("change", stills);

const form = document.getElementById("signup");
const status = document.getElementById("signup-status");
form.addEventListener("submit", (event) => {
  if (!form.action.includes("YOUR_FORM_ID")) return;
  event.preventDefault();
  status.textContent = "This signup is not connected yet. Replace YOUR_FORM_ID with a free Formspree form id.";
});
