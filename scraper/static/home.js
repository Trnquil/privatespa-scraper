const form = document.getElementById("scrape-form");
const urlInput = document.getElementById("url-input");
const scrapeBtn = document.getElementById("scrape-btn");
const statusEl = document.getElementById("status");
const spaListEl = document.getElementById("spa-list");
const spaListStatusEl = document.getElementById("spa-list-status");
const spaListCountEl = document.getElementById("spa-list-count");
const spaSearchInput = document.getElementById("spa-search");
const refreshSpasBtn = document.getElementById("refresh-spas-btn");
const createSpaBtn = document.getElementById("create-spa-btn");

let allSpas = [];

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

function spaMatchesQuery(spa, query) {
  const haystack = [
    spa.name,
    spa.canton,
    spa.location,
    spa.website,
    spa.id,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return haystack.includes(query);
}

function updateSpaListCount(shown, total, query) {
  if (!total) {
    spaListCountEl.classList.add("hidden");
    return;
  }

  if (query) {
    spaListCountEl.textContent = `${shown} of ${total} spas`;
  } else {
    spaListCountEl.textContent = `${total} spas`;
  }
  spaListCountEl.classList.remove("hidden");
}

function renderSpaList(spas) {
  spaListEl.innerHTML = "";
  const query = spaSearchInput.value.trim().toLowerCase();
  const filtered = query ? spas.filter((spa) => spaMatchesQuery(spa, query)) : spas;

  updateSpaListCount(filtered.length, spas.length, query);

  if (!spas.length) {
    spaListCountEl.classList.add("hidden");
    spaListEl.innerHTML = '<p class="spa-list-empty">No spas found in Firestore.</p>';
    return;
  }

  if (!filtered.length) {
    spaListEl.innerHTML = '<p class="spa-list-empty">No spas match your search.</p>';
    return;
  }

  for (const spa of filtered) {
    const link = document.createElement("a");
    link.className = "spa-list-item";
    link.href = `/spa/${encodeURIComponent(spa.id)}`;

    const header = document.createElement("div");
    header.className = "spa-list-item-header";

    const title = document.createElement("strong");
    title.textContent = spa.name || "Untitled";

    header.appendChild(title);

    if (spa.premium) {
      const premiumIcon = document.createElement("span");
      premiumIcon.className = "spa-premium-icon";
      premiumIcon.textContent = "★";
      premiumIcon.setAttribute("aria-label", "Premium spa");
      premiumIcon.title = "Premium spa";
      header.appendChild(premiumIcon);
    }

    if (!spa.complete) {
      const icon = document.createElement("span");
      icon.className = "spa-incomplete-icon";
      icon.textContent = "!";
      icon.setAttribute("aria-label", "Incomplete spa information");
      icon.title = `Missing: ${(spa.missing_fields || []).join(", ")}`;
      header.appendChild(icon);
    }

    const meta = document.createElement("span");
    const metaParts = [spa.canton, spa.location].filter(Boolean);
    meta.textContent = metaParts.join(" · ") || spa.website || spa.id;

    link.appendChild(header);
    link.appendChild(meta);
    spaListEl.appendChild(link);
  }
}

async function loadSpaList() {
  refreshSpasBtn.disabled = true;
  createSpaBtn.disabled = true;
  setSpaListStatus("Loading spas from Firestore…", "loading");

  try {
    const response = await fetch("/api/spas");
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to load spas");
    }

    allSpas = result.spas || [];
    clearSpaListStatus();
    renderSpaList(allSpas);
  } catch (error) {
    setSpaListStatus(error.message, "error");
    spaListEl.innerHTML = "";
    spaListCountEl.classList.add("hidden");
  } finally {
    refreshSpasBtn.disabled = false;
    createSpaBtn.disabled = false;
  }
}

async function createSpa() {
  createSpaBtn.disabled = true;
  refreshSpasBtn.disabled = true;
  setSpaListStatus("Creating new spa…", "loading");

  try {
    const response = await fetch("/api/spas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ data: { name: "Untitled", premium: false } }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to create spa");
    }

    window.location.href = `/spa/${encodeURIComponent(result.id)}`;
  } catch (error) {
    setSpaListStatus(error.message, "error");
    createSpaBtn.disabled = false;
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

spaSearchInput.addEventListener("input", () => {
  renderSpaList(allSpas);
});

refreshSpasBtn.addEventListener("click", loadSpaList);
createSpaBtn.addEventListener("click", createSpa);
loadSpaList();
