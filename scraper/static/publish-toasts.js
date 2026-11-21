// Background publish notifications, shown top right on every portal page.
(() => {
  const KEY = "pendingPublishJobs";
  const read = () => {
    try { return JSON.parse(sessionStorage.getItem(KEY) || "[]"); } catch { return []; }
  };
  const write = (jobs) => {
    try { sessionStorage.setItem(KEY, JSON.stringify(jobs)); } catch {}
  };

  // Styles live here (not in style.css) so a cached stylesheet can never hide notifications.
  const css = `
.toasts{position:fixed;top:1rem;right:1rem;z-index:10000;display:flex;flex-direction:column;gap:.5rem;max-width:380px}
.toast{display:flex;align-items:flex-start;gap:.75rem;padding:.8rem 1rem;border-radius:10px;background:#fff;color:#1a1a1a;
  box-shadow:0 8px 28px rgba(0,0,0,.18);font:500 .9rem/1.4 system-ui,sans-serif;border-left:4px solid #2e7d32;animation:toast-in .2s ease-out}
.toast-error{border-left-color:#c62828}
.toast-info{border-left-color:#777}
.toast a,.toast span{flex:1;color:inherit;text-decoration:none}
.toast-close{border:0;background:none;cursor:pointer;color:#888;padding:0;font-size:.9rem}
@keyframes toast-in{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}`;

  let box = null;
  function container() {
    if (!box) {
      const style = document.createElement("style");
      style.textContent = css;
      document.head.appendChild(style);
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
    if (kind !== "error") setTimeout(() => t.remove(), 8000);
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
        const rejecting = j.kind === "reject";
        if (j.state === "done") toast(`${rejecting ? "Rejected" : "Published"}: ${j.name}`, rejecting ? "info" : "success");
        else if (j.state === "failed")
          toast(
            `Could not ${rejecting ? "reject" : "publish"} ${j.name}: ${j.error} (click to open)`,
            "error",
            `/spa/${encodeURIComponent(j.spa_id)}`,
          );
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
