const form = document.getElementById("scrape-form");
const urlInput = document.getElementById("url-input");
const scrapeBtn = document.getElementById("scrape-btn");
const statusEl = document.getElementById("status");
const spaListEl = document.getElementById("spa-list");
const spaListStatusEl = document.getElementById("spa-list-status");
const refreshSpasBtn = document.getElementById("refresh-spas-btn");

function normalizeUrl(url) {
  const trimmed = url.trim();
  if (!trimmed) return trimmed;
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
  statusEl.classList.remove("hidden");
}

function setSpaListStatus(message, type) {
  spaListStatusEl.textContent = message;
  spaListStatusEl.className = `status ${type}`;
  spaListStatusEl.classList.remove("hidden");
}

function clearSpaListStatus() {
  spaListStatusEl.classList.add("hidden");
}

function renderSpaList(spas) {
  spaListEl.innerHTML = "";

  if (!spas.length) {
    spaListEl.innerHTML = '<p class="spa-list-empty">No spas found in Firestore.</p>';
    return;
  }

  for (const spa of spas) {
    const link = document.createElement("a");
    link.className = "spa-list-item";
    link.href = `/spa/${encodeURIComponent(spa.id)}`;

    const title = document.createElement("strong");
    title.textContent = spa.name || "Untitled";

    const meta = document.createElement("span");
    const metaParts = [spa.canton, spa.location].filter(Boolean);
    meta.textContent = metaParts.join(" · ") || spa.website || spa.id;

    link.appendChild(title);
    link.appendChild(meta);
    spaListEl.appendChild(link);
  }
}

async function loadSpaList() {
  refreshSpasBtn.disabled = true;
  setSpaListStatus("Loading spas from Firestore…", "loading");

  try {
    const response = await fetch("/api/spas");
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to load spas");
    }

    clearSpaListStatus();
    renderSpaList(result.spas || []);
  } catch (error) {
    setSpaListStatus(error.message, "error");
    spaListEl.innerHTML = "";
  } finally {
    refreshSpasBtn.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = normalizeUrl(urlInput.value);
  if (!url) return;

  urlInput.value = url;
  scrapeBtn.disabled = true;
  setStatus("Scraping… this may take up to a minute.", "loading");

  try {
    const response = await fetch("/api/scrape", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Scrape failed");
    }

    sessionStorage.setItem("scrapeResult", JSON.stringify(result));
    window.location.href = "/scrape/edit";
  } catch (error) {
    setStatus(error.message, "error");
    scrapeBtn.disabled = false;
  }
});

urlInput.addEventListener("blur", () => {
  const normalized = normalizeUrl(urlInput.value);
  if (normalized) urlInput.value = normalized;
});

refreshSpasBtn.addEventListener("click", loadSpaList);
loadSpaList();
