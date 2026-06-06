const form = document.getElementById("scrape-form");
const urlInput = document.getElementById("url-input");
const scrapeBtn = document.getElementById("scrape-btn");
const statusEl = document.getElementById("status");
const editorEl = document.getElementById("editor");
const downloadBtn = document.getElementById("download-btn");
const imageListEl = document.getElementById("image-list");
const newImageUrlInput = document.getElementById("new-image-url");
const addImageBtn = document.getElementById("add-image-btn");
const lightboxEl = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxCloseBtn = document.getElementById("lightbox-close");
const lightboxPrevBtn = document.getElementById("lightbox-prev");
const lightboxNextBtn = document.getElementById("lightbox-next");

let lightboxIndex = 0;

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

function getImageUrls() {
  return [...imageListEl.querySelectorAll(".image-url-input")]
    .map((input) => input.value.trim())
    .filter(Boolean);
}

function openLightboxAtIndex(index) {
  const urls = getImageUrls();
  if (!urls.length) return;

  lightboxIndex = Math.max(0, Math.min(index, urls.length - 1));
  lightboxImg.src = urls[lightboxIndex];
  lightboxEl.classList.remove("hidden");
  lightboxEl.setAttribute("aria-hidden", "false");
  document.body.classList.add("lightbox-open");
  updateLightboxNav();
}

function updateLightboxNav() {
  const urls = getImageUrls();
  const hasMultiple = urls.length > 1;
  lightboxPrevBtn.classList.toggle("hidden", !hasMultiple);
  lightboxNextBtn.classList.toggle("hidden", !hasMultiple);
  lightboxPrevBtn.disabled = lightboxIndex <= 0;
  lightboxNextBtn.disabled = lightboxIndex >= urls.length - 1;
}

function showLightboxRelative(step) {
  const urls = getImageUrls();
  if (!urls.length) return;
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
    const cards = [...imageListEl.querySelectorAll(".image-card")];
    openLightboxAtIndex(cards.indexOf(card));
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

function populateEditor(result) {
  const data = result.data || {};

  fields.name.value = data.name || "";
  fields.description.value = data.description || "";
  fields.location.value = data.location || "";
  fields.canton.value = data.canton || "";
  fields.website.value = data.website || "";
  fields.latitude.value = data.coordinates?.[0] ?? "";
  fields.longitude.value = data.coordinates?.[1] ?? "";
  fields.amenities.value = arrayToLines(data.amenities);
  fields.rawPreview.value = result.raw_text_preview || "";

  document.getElementById("meta-playwright").textContent = result.used_playwright
    ? "Fetched with Playwright"
    : "Fetched with httpx";
  document.getElementById("meta-source").textContent = result.source_url || "";

  renderImages(data.images);
  newImageUrlInput.value = "";
  editorEl.classList.remove("hidden");
}

function buildExportJson() {
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

function downloadJson() {
  const payload = buildExportJson();
  const slug = (payload.data.name || "spa")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const filename = `${slug || "spa"}.json`;
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const url = normalizeUrl(urlInput.value);
  if (!url) return;

  urlInput.value = url;
  scrapeBtn.disabled = true;
  editorEl.classList.add("hidden");
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

    clearStatus();
    populateEditor(result);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    scrapeBtn.disabled = false;
  }
});

downloadBtn.addEventListener("click", downloadJson);

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

urlInput.addEventListener("blur", () => {
  const normalized = normalizeUrl(urlInput.value);
  if (normalized) urlInput.value = normalized;
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
