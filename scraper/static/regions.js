const bodyEl = document.getElementById("regions-body");
const summaryEl = document.getElementById("crawl-summary");
const crawlNextBtn = document.getElementById("crawl-next-btn");
const jobEl = document.getElementById("crawl-job");
const jobTitleEl = document.getElementById("crawl-job-title");
const logEl = document.getElementById("crawl-log");
const statusEl = document.getElementById("status");
const candidatesEl = document.getElementById("candidates");
const candidatesTitleEl = document.getElementById("candidates-title");
const candidatesBodyEl = document.getElementById("candidates-body");

const CANDIDATE_LABELS = {
  draft_created: "New draft",
  not_private: "Not a private spa",
  accepted: "Published",
  rejected: "Rejected",
  duplicate: "Already listed",
  no_website: "No website",
  skipped: "Skipped",
  failed: "Scrape failed",
};

let pollTimer = null;

function setStatus(message, type = "error") {
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;
}

function clearStatus() {
  statusEl.className = "status hidden";
}

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("de-CH", { dateStyle: "short", timeStyle: "short" });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}

function renderRegions(regions, job) {
  const done = regions.filter((r) => r.status === "done").length;
  const drafts = regions.reduce((sum, r) => sum + (r.drafts || 0), 0);
  const next = regions.find((r) => r.status === "todo");
  summaryEl.textContent = `${done} of ${regions.length} cantons done · ${drafts} drafts created · next: ${
    next ? next.name : "none"
  }`;
  crawlNextBtn.disabled = job.running || !next;

  bodyEl.innerHTML = "";
  for (const r of regions) {
    const tr = document.createElement("tr");

    const nameTd = el("td");
    const nameBtn = el("button", r.name, "link-btn");
    nameBtn.title = "Show what was found";
    nameBtn.addEventListener("click", () => showCandidates(r));
    nameTd.appendChild(nameBtn);
    tr.appendChild(nameTd);

    const statusTd = el("td");
    statusTd.appendChild(el("span", r.status, `region-status region-${r.status}`));
    if (r.saturated) {
      const warn = el("span", " ⚠", "region-warning");
      warn.title = "Google returned its maximum of 60 results; some spas may be missing";
      statusTd.appendChild(warn);
    }
    if (r.error) statusTd.title = r.error;
    tr.appendChild(statusTd);

    tr.appendChild(el("td", formatDate(r.last_crawled)));
    tr.appendChild(el("td", r.results ?? "—", "num"));
    tr.appendChild(el("td", r.drafts ?? "—", "num"));

    const prioTd = el("td", null, "num");
    const prio = document.createElement("input");
    prio.type = "number";
    prio.value = r.priority;
    prio.className = "priority-input";
    prio.title = "Higher runs first";
    prio.addEventListener("change", async () => {
      try {
        await api(`/api/regions/${r.id}/priority`, {
          method: "POST",
          body: JSON.stringify({ priority: Number(prio.value) }),
        });
        load();
      } catch (e) {
        setStatus(e.message);
      }
    });
    prioTd.appendChild(prio);
    tr.appendChild(prioTd);

    const actionsTd = el("td", null, "actions");
    const crawlBtn = el("button", r.status === "done" ? "Crawl again" : "Crawl", "secondary-btn");
    crawlBtn.disabled = job.running;
    crawlBtn.addEventListener("click", () => startCrawl(r.id));
    actionsTd.appendChild(crawlBtn);
    if (r.status === "done" || r.status === "failed") {
      const resetBtn = el("button", "Mark todo", "secondary-btn");
      resetBtn.disabled = job.running;
      resetBtn.addEventListener("click", async () => {
        await api(`/api/regions/${r.id}/reset`, { method: "POST" });
        load();
      });
      actionsTd.appendChild(resetBtn);
    }
    tr.appendChild(actionsTd);
    bodyEl.appendChild(tr);
  }
}

function renderJob(job) {
  if (!job.running && !job.log.length) {
    jobEl.classList.add("hidden");
    return;
  }
  jobEl.classList.remove("hidden");
  jobTitleEl.textContent = job.running ? "Crawl running…" : job.error ? "Crawl failed" : "Last crawl";
  logEl.textContent = job.log.join("\n");
  logEl.scrollTop = logEl.scrollHeight;
}

async function load() {
  try {
    const { regions, job } = await api("/api/regions");
    renderRegions(regions, job);
    renderJob(job);
    clearTimeout(pollTimer);
    if (job.running) pollTimer = setTimeout(load, 2000);
  } catch (e) {
    setStatus(e.message);
  }
}

async function startCrawl(regionId) {
  clearStatus();
  try {
    await api("/api/crawl", {
      method: "POST",
      body: JSON.stringify(regionId ? { region: regionId } : {}),
    });
    load();
  } catch (e) {
    setStatus(e.message);
  }
}

async function showCandidates(region) {
  try {
    const { candidates } = await api(`/api/regions/${region.id}/candidates`);
    candidatesTitleEl.textContent = `${region.name}: ${candidates.length} places found`;
    candidatesBodyEl.innerHTML = "";
    if (!candidates.length) {
      const tr = el("tr");
      tr.appendChild(el("td", "Not crawled yet."));
      candidatesBodyEl.appendChild(tr);
    }
    for (const c of candidates) {
      const tr = document.createElement("tr");
      tr.appendChild(el("td", CANDIDATE_LABELS[c.status] || c.status, `candidate-${c.status}`));
      const nameTd = el("td");
      if (c.spa_id) {
        const a = el("a", c.name || c.spa_id);
        a.href = `/spa/${encodeURIComponent(c.spa_id)}`;
        nameTd.appendChild(a);
      } else {
        nameTd.textContent = c.name || "—";
      }
      tr.appendChild(nameTd);
      const siteTd = el("td");
      if (c.website) {
        const a = el("a", c.website.replace(/^https?:\/\/(www\.)?/, ""));
        a.href = c.website;
        a.target = "_blank";
        a.rel = "noopener";
        siteTd.appendChild(a);
      } else {
        siteTd.textContent = c.address || "—";
      }
      tr.appendChild(siteTd);
      tr.appendChild(el("td", c.note || ""));
      candidatesBodyEl.appendChild(tr);
    }
    candidatesEl.classList.remove("hidden");
    candidatesEl.scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    setStatus(e.message);
  }
}

crawlNextBtn.addEventListener("click", () => startCrawl(null));
load();
