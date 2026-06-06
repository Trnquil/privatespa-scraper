const form = document.getElementById("scrape-form");
const urlInput = document.getElementById("url-input");
const scrapeBtn = document.getElementById("scrape-btn");
const statusEl = document.getElementById("status");
const editorEl = document.getElementById("editor");
const downloadBtn = document.getElementById("download-btn");
const imagePreviewsEl = document.getElementById("image-previews");

const fields = {
  name: document.getElementById("name"),
  description: document.getElementById("description"),
  location: document.getElementById("location"),
  canton: document.getElementById("canton"),
  website: document.getElementById("website"),
  latitude: document.getElementById("latitude"),
  longitude: document.getElementById("longitude"),
  amenities: document.getElementById("amenities"),
  images: document.getElementById("images"),
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
  fields.images.value = arrayToLines(data.images);
  fields.rawPreview.value = result.raw_text_preview || "";

  document.getElementById("meta-playwright").textContent = result.used_playwright
    ? "Fetched with Playwright"
    : "Fetched with httpx";
  document.getElementById("meta-source").textContent = result.source_url || "";

  updateImagePreviews();
  editorEl.classList.remove("hidden");
}

function updateImagePreviews() {
  imagePreviewsEl.innerHTML = "";
  for (const url of linesToArray(fields.images.value)) {
    const img = document.createElement("img");
    img.src = url;
    img.alt = "Preview";
    img.loading = "lazy";
    img.onerror = () => {
      img.style.opacity = "0.35";
    };
    imagePreviewsEl.appendChild(img);
  }
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
      images: linesToArray(fields.images.value),
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
  const url = urlInput.value.trim();
  if (!url) return;

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
fields.images.addEventListener("input", updateImagePreviews);
