const statusEl = document.getElementById("status");
const saveSpaBtn = document.getElementById("save-spa-btn");
const editorTitleEl = document.getElementById("editor-title");
const metaModeEl = document.getElementById("meta-mode");
const rawPreviewFieldEl = document.getElementById("raw-preview-field");
const imageListEl = document.getElementById("image-list");
const newImageUrlInput = document.getElementById("new-image-url");
const addImageBtn = document.getElementById("add-image-btn");
const lightboxEl = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxCloseBtn = document.getElementById("lightbox-close");
const lightboxPrevBtn = document.getElementById("lightbox-prev");
const lightboxNextBtn = document.getElementById("lightbox-next");
const lightboxDeleteBtn = document.getElementById("lightbox-delete");

const editorConfig = JSON.parse(
  document.getElementById("editor-config").textContent
);

let lightboxIndex = 0;
let currentSpaId = editorConfig.spaId || null;
let editorMode = editorConfig.mode || "firestore";

const fields = {
  name: document.getElementById("name"),
  description: document.getElementById("description"),
  location: document.getElementById("location"),
  canton: document.getElementById("canton"),
  website: document.getElementById("website"),
  latitude: document.getElementById("latitude"),
  longitude: document.getElementById("longitude"),
  amenities: document.getElementById("amenities"),
  rawPreview: document.getElementById("raw-preview"),
};

function setStatus(message, type) {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
  statusEl.classList.remove("hidden");
}

function clearStatus() {
  statusEl.classList.add("hidden");
}

function linesToArray(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function arrayToLines(items) {
  return (items || []).join("\n");
}

function getImageCards() {
  return [...imageListEl.querySelectorAll(".image-card")];
}

function getImageUrlFromCard(card) {
  return card.querySelector(".image-url-input").value.trim();
}

function getImageUrls() {
  return getImageCards().map(getImageUrlFromCard).filter(Boolean);
}

function removeImageAtIndex(index) {
  const cards = getImageCards();
  const card = cards[index];
  if (!card) return;

  card.remove();

  if (!getImageCards().length) {
    closeLightbox();
    return;
  }

  openLightboxAtIndex(Math.min(index, getImageCards().length - 1));
}

function deleteCurrentLightboxImage() {
  removeImageAtIndex(lightboxIndex);
}

function openLightboxAtIndex(index) {
  const cards = getImageCards();
  if (!cards.length) return;

  lightboxIndex = Math.max(0, Math.min(index, cards.length - 1));
  lightboxImg.src = getImageUrlFromCard(cards[lightboxIndex]);
  lightboxEl.classList.remove("hidden");
  lightboxEl.setAttribute("aria-hidden", "false");
  document.body.classList.add("lightbox-open");
  updateLightboxNav();
}

function updateLightboxNav() {
  const cards = getImageCards();
  const hasMultiple = cards.length > 1;
  lightboxPrevBtn.classList.toggle("hidden", !hasMultiple);
  lightboxNextBtn.classList.toggle("hidden", !hasMultiple);
  lightboxPrevBtn.disabled = lightboxIndex <= 0;
  lightboxNextBtn.disabled = lightboxIndex >= cards.length - 1;
}

function showLightboxRelative(step) {
  if (!getImageCards().length) return;
  openLightboxAtIndex(lightboxIndex + step);
}

function closeLightbox() {
  lightboxEl.classList.add("hidden");
  lightboxEl.setAttribute("aria-hidden", "true");
  lightboxImg.removeAttribute("src");
  lightboxIndex = 0;
  document.body.classList.remove("lightbox-open");
}

function createImageCard(url) {
  const card = document.createElement("div");
  card.className = "image-card";

  const previewWrap = document.createElement("div");
  previewWrap.className = "image-card-preview";

  const img = document.createElement("img");
  img.src = url;
  img.alt = "Preview";
  img.loading = "lazy";
  img.onerror = () => {
    img.classList.add("broken");
  };
  img.addEventListener("click", () => {
    openLightboxAtIndex(getImageCards().indexOf(card));
  });

  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "image-remove-btn";
  removeBtn.setAttribute("aria-label", "Remove image");
  removeBtn.textContent = "×";
  removeBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    card.remove();
  });

  previewWrap.appendChild(img);
  previewWrap.appendChild(removeBtn);

  const urlInputEl = document.createElement("input");
  urlInputEl.type = "text";
  urlInputEl.className = "image-url-input";
  urlInputEl.value = url;
  urlInputEl.placeholder = "Image URL";
  urlInputEl.addEventListener("input", () => {
    img.src = urlInputEl.value.trim();
    img.classList.remove("broken");
  });

  card.appendChild(previewWrap);
  card.appendChild(urlInputEl);
  return card;
}

function renderImages(urls) {
  imageListEl.innerHTML = "";
  for (const url of urls || []) {
    imageListEl.appendChild(createImageCard(url));
  }
}

function addImage(url) {
  const normalized = url.trim();
  if (!normalized) return;
  imageListEl.appendChild(createImageCard(normalized));
}

function populateEditor(result, options = {}) {
  const data = result.data || {};
  editorMode = options.mode || editorMode;
  currentSpaId = options.spaId || result.id || currentSpaId;

  fields.name.value = data.name || "";
  fields.description.value = data.description || "";
  fields.location.value = data.location || "";
  fields.canton.value = data.canton || "";
  fields.website.value = data.website || "";
  fields.latitude.value = data.coordinates?.[0] ?? "";
  fields.longitude.value = data.coordinates?.[1] ?? "";
  fields.amenities.value = arrayToLines(data.amenities);
  fields.rawPreview.value = result.raw_text_preview || "";

  if (editorMode === "firestore") {
    editorTitleEl.textContent = data.name || "Edit spa";
    metaModeEl.textContent = `Firebase ID: ${currentSpaId}`;
    document.getElementById("meta-playwright").textContent = "";
    document.getElementById("meta-source").textContent = data.website || "";
    rawPreviewFieldEl.classList.add("hidden");
  } else {
    editorTitleEl.textContent = data.name || "New scraped spa";
    metaModeEl.textContent = "New scrape";
    document.getElementById("meta-playwright").textContent = result.used_playwright
      ? "Fetched with Playwright"
      : "Fetched with httpx";
    document.getElementById("meta-source").textContent = result.source_url || "";
    rawPreviewFieldEl.classList.remove("hidden");
  }

  renderImages(data.images);
  newImageUrlInput.value = "";
}

function buildSpaPayload() {
  const lat = fields.latitude.value.trim();
  const lng = fields.longitude.value.trim();
  let coordinates = null;

  if (lat && lng) {
    const latitude = parseFloat(lat);
    const longitude = parseFloat(lng);
    if (!Number.isNaN(latitude) && !Number.isNaN(longitude)) {
      coordinates = [latitude, longitude];
    }
  }

  return {
    data: {
      amenities: linesToArray(fields.amenities.value),
      canton: fields.canton.value.trim() || null,
      coordinates,
      description: fields.description.value.trim() || null,
      images: getImageUrls(),
      location: fields.location.value.trim() || null,
      name: fields.name.value.trim() || null,
      website: fields.website.value.trim() || null,
    },
  };
}

async function saveSpa() {
  saveSpaBtn.disabled = true;
  setStatus("Saving to Firebase…", "loading");

  try {
    const payload = buildSpaPayload();
    const isNew = !currentSpaId;
    const url = isNew
      ? "/api/spas"
      : `/api/spas/${encodeURIComponent(currentSpaId)}`;
    const method = isNew ? "POST" : "PUT";

    const response = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to save spa");
    }

    if (isNew) {
      sessionStorage.removeItem("scrapeResult");
      window.location.href = `/spa/${encodeURIComponent(result.id)}`;
      return;
    }

    clearStatus();
    populateEditor(result, { mode: "firestore", spaId: result.id });
    setStatus("Saved to Firebase.", "loading");
    setTimeout(clearStatus, 2000);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    saveSpaBtn.disabled = false;
  }
}

function loadScrapeResult() {
  const raw = sessionStorage.getItem("scrapeResult");
  if (!raw) {
    setStatus("No scrape result found. Go back and scrape a URL first.", "error");
    return;
  }

  try {
    const result = JSON.parse(raw);
    populateEditor(result, { mode: "scrape" });
  } catch {
    setStatus("Could not load scrape result.", "error");
  }
}

async function loadSpa(spaId) {
  setStatus("Loading spa…", "loading");

  try {
    const response = await fetch(`/api/spas/${encodeURIComponent(spaId)}`);
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to load spa");
    }

    clearStatus();
    populateEditor(result, { mode: "firestore", spaId });
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function initEditor() {
  if (editorMode === "firestore") {
    if (!currentSpaId) {
      setStatus("Missing spa ID.", "error");
      return;
    }
    await loadSpa(currentSpaId);
    return;
  }

  loadScrapeResult();
}

saveSpaBtn.addEventListener("click", saveSpa);

addImageBtn.addEventListener("click", () => {
  addImage(newImageUrlInput.value);
  newImageUrlInput.value = "";
  newImageUrlInput.focus();
});

newImageUrlInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    addImage(newImageUrlInput.value);
    newImageUrlInput.value = "";
  }
});

lightboxCloseBtn.addEventListener("click", closeLightbox);
lightboxPrevBtn.addEventListener("click", (event) => {
  event.stopPropagation();
  showLightboxRelative(-1);
});
lightboxNextBtn.addEventListener("click", (event) => {
  event.stopPropagation();
  showLightboxRelative(1);
});
lightboxDeleteBtn.addEventListener("click", (event) => {
  event.stopPropagation();
  deleteCurrentLightboxImage();
});

lightboxEl.addEventListener("click", (event) => {
  if (event.target === lightboxEl) closeLightbox();
});

document.addEventListener("keydown", (event) => {
  if (lightboxEl.classList.contains("hidden")) return;

  if (event.key === "Escape") {
    closeLightbox();
  } else if (event.key === "ArrowLeft") {
    showLightboxRelative(-1);
  } else if (event.key === "ArrowRight") {
    showLightboxRelative(1);
  }
});

initEditor();
