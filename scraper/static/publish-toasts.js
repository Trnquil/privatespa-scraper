// Background publish notifications, shown top right on every portal page.
(() => {
  const KEY = "pendingPublishJobs";
  const read = () => {
    try { return JSON.parse(sessionStorage.getItem(KEY) || "[]"); } catch { return []; }
  };
  const write = (jobs) => {
    try { sessionStorage.setItem(KEY, JSON.stringify(jobs)); } catch {}
  };

  let box = null;
  function container() {
    if (!box) {
      box = document.createElement("div");
      box.className = "toasts";
      document.body.appendChild(box);
    }
    return box;
  }

  function toast(text, kind, href) {
    const t = document.createElement("div");
    t.className = `toast toast-${kind}`;
    const msg = document.createElement(href ? "a" : "span");
    msg.textContent = text;
    if (href) msg.href = href;
    t.appendChild(msg);
    const close = document.createElement("button");
    close.textContent = "✕";
    close.className = "toast-close";
    close.addEventListener("click", () => t.remove());
    t.appendChild(close);
    container().appendChild(t);
    if (kind !== "error") setTimeout(() => t.remove(), 6000);
  }

  async function poll() {
    const pending = read();
    if (!pending.length) return;
    try {
      const res = await fetch(`/api/publish-jobs?ids=${encodeURIComponent(pending.map((j) => j.id).join(","))}`);
      const { jobs } = await res.json();
      const byId = Object.fromEntries(jobs.map((j) => [j.id, j]));
      const still = [];
      for (const p of pending) {
        const j = byId[p.id];
        if (!j) continue; // portal restarted: nothing to report
        if (j.state === "done") toast(`Published: ${j.name}`, "success");
        else if (j.state === "failed")
          toast(`Could not publish ${j.name}: ${j.error} (click to open)`, "error", `/spa/${encodeURIComponent(j.spa_id)}`);
        else still.push(p);
      }
      write(still);
    } catch {}
    if (read().length) setTimeout(poll, 1500);
  }

  window.publishToasts = {
    /** Spa ids currently being published (to skip them in the review list). */
    pendingSpaIds: () => read().map((j) => j.spa_id),
    track(job) {
      write([...read(), { id: job.id, spa_id: job.spa_id }]);
    },
    toast,
    poll,
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", poll);
  else poll();
})();
