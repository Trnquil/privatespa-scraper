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
const openSchemaBtn = document.getElementById("open-schema-btn");
const schemaModalEl = document.getElementById("schema-modal");
const closeSchemaBtn = document.getElementById("close-schema-btn");
const schemaFieldsEl = document.getElementById("schema-fields");
const schemaStatusEl = document.getElementById("schema-status");
const refreshSchemaBtn = document.getElementById("refresh-schema-btn");
const schemaAddForm = document.getElementById("schema-add-form");
const schemaFieldNameInput = document.getElementById("schema-field-name");
const schemaFieldTypeSelect = document.getElementById("schema-field-type");
const schemaFieldLabelInput = document.getElementById("schema-field-label");
const schemaAddBtn = document.getElementById("schema-add-btn");
const discoveredFieldsSection = document.getElementById("discovered-fields");
const discoveredFieldsListEl = document.getElementById("discovered-fields-list");

let allSpas = [];
let schemaFields = [];
let discoveredFields = [];

const TYPE_LABELS = {
  string: "String",
  number: "Number",
  boolean: "Boolean",
  array: "List",
  coordinates: "Coordinates",
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

function setSpaListStatus(message, type) {
  spaListStatusEl.textContent = message;
  spaListStatusEl.className = `status ${type}`;
  spaListStatusEl.classList.remove("hidden");
}

function clearSpaListStatus() {
  spaListStatusEl.classList.add("hidden");
}

function setSchemaStatus(message, type) {
  schemaStatusEl.textContent = message;
  schemaStatusEl.className = `status ${type}`;
  schemaStatusEl.classList.remove("hidden");
}

function clearSchemaStatus() {
  schemaStatusEl.classList.add("hidden");
}

function openSchemaModal() {
  schemaModalEl.classList.remove("hidden");
  schemaModalEl.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  loadSchema();
}

function closeSchemaModal() {
  schemaModalEl.classList.add("hidden");
  schemaModalEl.setAttribute("aria-hidden", "true");
  document.body.classList.remove("modal-open");
}

function renderSchemaFieldRow(field, options = {}) {
  const row = document.createElement("div");
  row.className = "schema-field-row";

  const main = document.createElement("div");
  main.className = "schema-field-main";

  const name = document.createElement("code");
  name.className = "schema-field-name";
  name.textContent = field.name;

  const label = document.createElement("span");
  label.className = "schema-field-label";
  label.textContent = field.label || field.name;

  const type = document.createElement("span");
  type.className = "schema-field-type";
  type.textContent = TYPE_LABELS[field.type] || field.type;

  main.appendChild(name);
  main.appendChild(label);
  main.appendChild(type);

  if (field.inferred_types?.length > 1) {
    const hint = document.createElement("span");
    hint.className = "schema-field-hint";
    hint.textContent = `Mixed types: ${field.inferred_types.join(", ")}`;
    main.appendChild(hint);
  }

  row.appendChild(main);

  const actions = document.createElement("div");
  actions.className = "schema-field-actions";

  if (field.builtin) {
    const badge = document.createElement("span");
    badge.className = "schema-badge schema-badge-builtin";
    badge.textContent = "Built-in";
    actions.appendChild(badge);
  } else if (options.discovered) {
    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "secondary-btn schema-add-discovered-btn";
    addBtn.textContent = "Add to schema";
    addBtn.addEventListener("click", () => {
      schemaFieldNameInput.value = field.name;
      schemaFieldTypeSelect.value = field.type || "string";
      schemaFieldLabelInput.value = field.label || "";
      schemaFieldNameInput.focus();
    });
    actions.appendChild(addBtn);
  } else {
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "schema-delete-btn";
    deleteBtn.textContent = "Remove";
    deleteBtn.addEventListener("click", () => removeSchemaField(field.name));
    actions.appendChild(deleteBtn);
  }

  row.appendChild(actions);
  return row;
}

function renderSchema(fields, discovered) {
  schemaFieldsEl.innerHTML = "";

  if (!fields.length) {
    schemaFieldsEl.innerHTML = '<p class="schema-empty">No fields defined.</p>';
  } else {
    for (const field of fields) {
      schemaFieldsEl.appendChild(renderSchemaFieldRow(field));
    }
  }

  discoveredFieldsListEl.innerHTML = "";
  if (!discovered.length) {
    discoveredFieldsSection.classList.add("hidden");
    return;
  }

  discoveredFieldsSection.classList.remove("hidden");
  for (const field of discovered) {
    discoveredFieldsListEl.appendChild(
      renderSchemaFieldRow(field, { discovered: true })
    );
  }
}

async function loadSchema() {
  refreshSchemaBtn.disabled = true;
  schemaAddBtn.disabled = true;
  setSchemaStatus("Loading schema…", "loading");

  try {
    const response = await fetch("/api/schema");
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to load schema");
    }

    schemaFields = result.fields || [];
    discoveredFields = result.discovered || [];
    clearSchemaStatus();
    renderSchema(schemaFields, discoveredFields);
  } catch (error) {
    setSchemaStatus(error.message, "error");
    schemaFieldsEl.innerHTML = "";
    discoveredFieldsSection.classList.add("hidden");
  } finally {
    refreshSchemaBtn.disabled = false;
    schemaAddBtn.disabled = false;
  }
}

async function addSchemaField(event) {
  event.preventDefault();

  const name = schemaFieldNameInput.value.trim();
  const type = schemaFieldTypeSelect.value;
  const label = schemaFieldLabelInput.value.trim();

  if (!name) return;

  schemaAddBtn.disabled = true;
  refreshSchemaBtn.disabled = true;
  setSchemaStatus("Adding field…", "loading");

  try {
    const response = await fetch("/api/schema", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, type, label: label || undefined }),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to add field");
    }

    schemaFields = result.fields || [];
    discoveredFields = result.discovered || [];
    schemaFieldNameInput.value = "";
    schemaFieldLabelInput.value = "";
    schemaFieldTypeSelect.value = "string";
    clearSchemaStatus();
    renderSchema(schemaFields, discoveredFields);
    setSchemaStatus(`Added field "${name}".`, "loading");
    setTimeout(clearSchemaStatus, 2000);
  } catch (error) {
    setSchemaStatus(error.message, "error");
  } finally {
    schemaAddBtn.disabled = false;
    refreshSchemaBtn.disabled = false;
  }
}

async function removeSchemaField(name) {
  const confirmed = window.confirm(
    `Remove "${name}" from the schema? This also deletes the field from all spa documents.`
  );
  if (!confirmed) return;

  refreshSchemaBtn.disabled = true;
  schemaAddBtn.disabled = true;
  setSchemaStatus(`Removing "${name}"…`, "loading");

  try {
    const response = await fetch(`/api/schema/${encodeURIComponent(name)}`, {
      method: "DELETE",
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Failed to remove field");
    }

    schemaFields = result.fields || [];
    discoveredFields = result.discovered || [];
    clearSchemaStatus();
    renderSchema(schemaFields, discoveredFields);
    await loadSpaList();
  } catch (error) {
    setSchemaStatus(error.message, "error");
  } finally {
    refreshSchemaBtn.disabled = false;
    schemaAddBtn.disabled = false;
  }
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

    if (spa.owner) {
      const ownerIcon = document.createElement("span");
      ownerIcon.className = "spa-owner-icon";
      ownerIcon.setAttribute("aria-label", "Has owner");
      ownerIcon.title = `Owner: ${spa.owner}`;
      header.appendChild(ownerIcon);
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
openSchemaBtn.addEventListener("click", openSchemaModal);
closeSchemaBtn.addEventListener("click", closeSchemaModal);
schemaModalEl.addEventListener("click", (event) => {
  if (event.target === schemaModalEl) closeSchemaModal();
});
refreshSchemaBtn.addEventListener("click", loadSchema);
schemaAddForm.addEventListener("submit", addSchemaField);
loadSpaList();
