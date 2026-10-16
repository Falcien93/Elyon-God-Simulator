const version = new URLSearchParams(location.search).get("version");
const node = document.getElementById("splash-version");
if (node && version) node.textContent = `Version ${version}`;
