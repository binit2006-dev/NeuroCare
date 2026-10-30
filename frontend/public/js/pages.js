/* NeuroCare pages: My Scans, About, Downloads */
(() => {
  const { $, esc, t, api, icons } = NC;

  /* ---------- My Scans ---------- */
  function scanCard(s) {
    const advice = NC.lang === "hi" ? s.advice_hi || s.advice : s.advice || s.advice_hi;
    const date = new Date(s.created_at).toLocaleString(NC.lang === "hi" ? "hi-IN" : undefined);
    return `
      <li class="card history-item" data-testid="history-item-${esc(s.id)}">
        <div class="xs muted">${esc(date)}</div>
        <div class="strong ${s.tumor_detected ? "" : "accent"}">${esc(t(`class_${s.tumor_type}`))}</div>
        <div class="small muted">${(s.confidence * 100).toFixed(1)}% ${esc(t("hist_conf"))} · ${esc(s.location || t("hist_no_location"))}</div>
        ${advice?.tumor_info?.overview ? `<p class="small clamp">${esc(advice.tumor_info.overview)}</p>` : ""}
      </li>`;
  }

  async function renderHistory() {
    NC.showView("view-history");
    const root = $("#history-root");
    const title = $("#history-title");
    if (!NC.authReady) { root.innerHTML = ""; return; }
    if (!NC.user) {
      title.textContent = t("hist_title");
      root.innerHTML = `
        <div class="card signin" data-testid="history-signin-prompt">
          <h2 class="h3">${esc(t("hist_signin_title"))}</h2><p class="muted">${esc(t("hist_signin_sub"))}</p>
          <button class="btn btn-primary" data-testid="history-signin-button" type="button"><i data-lucide="log-in"></i>${esc(t("hist_signin_btn"))}</button>
        </div>`;
      root.querySelector("button").onclick = NC.login;
      return icons();
    }
    title.innerHTML = `${esc(t("hist_hello"))} <span class="accent">${esc(NC.user.name.split(" ")[0])}.</span>`;
    root.innerHTML = `<p class="muted">${esc(t("loading"))}</p>`;
    let scans = [];
    try { scans = await api("/my-scans"); } catch (_) { /* show empty state */ }
    if (NC.route() !== "#/history") return;
    root.innerHTML = scans.length
      ? `<ul class="history-grid" data-testid="history-list">${scans.map(scanCard).join("")}</ul>`
      : `<div class="card dashed" data-testid="history-empty">${esc(t("hist_empty"))}
           <a href="#/" class="link" data-testid="history-start-scan">${esc(t("hist_start"))} <i data-lucide="arrow-right"></i></a></div>`;
    icons();
  }

  /* ---------- About ---------- */
  async function renderAbout() {
    NC.showView("view-about");
    const box = $("#model-status");
    box.innerHTML = `<span class="muted">${esc(t("checking"))}</span>`;
    try {
      const s = await api("/model-status");
      box.innerHTML = `
        <span class="muted">${esc(t("status_loaded"))}</span><span>${esc(s.model_loaded ? t("yes") : t("no_demo"))}</span>
        <span class="muted">${esc(t("model_file"))}</span><span>${esc(s.model_file || "—")}</span>
        <span class="muted">${esc(t("classes"))}</span><span>${esc((s.classes || []).join(" · "))}</span>`;
    } catch (_) { box.innerHTML = "—"; }
  }

  /* ---------- Downloads ---------- */
  const size = (b) => (b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`);
  const iconFor = (ext) => (["png", "jpg", "jpeg", "webp"].includes(ext) ? "image" : ["pdf", "txt", "md"].includes(ext) ? "file-text" : "file");

  async function renderDownloads() {
    NC.showView("view-downloads");
    const ul = $("#downloads-list");
    ul.innerHTML = `<li class="muted">${esc(t("loading"))}</li>`;
    let files = [];
    try { files = await api("/downloads"); } catch (_) { /* show empty state */ }
    ul.innerHTML = files.length
      ? files.map((f) => `
        <li class="card dl-item" data-testid="download-${esc(f.name)}">
          <span class="icon-square"><i data-lucide="${iconFor(f.ext)}"></i></span>
          <div class="grow"><div class="strong trunc">${esc(f.name)}</div><div class="xs muted">${esc(f.ext.toUpperCase())} · ${size(f.size_bytes)}</div></div>
          <a class="btn btn-primary btn-sm" href="/api/downloads/${encodeURIComponent(f.name)}" download data-testid="download-link-${esc(f.name)}"><i data-lucide="download"></i>${esc(t("dl_get"))}</a>
        </li>`).join("")
      : `<li class="card dashed" data-testid="downloads-empty">${esc(t("dl_empty"))} <code>backend/downloads/</code></li>`;
    icons();
  }

  NC.views["#/history"] = renderHistory;
  NC.views["#/about"] = renderAbout;
  NC.views["#/downloads"] = renderDownloads;

  const rerender = () => { const v = NC.views[NC.route()]; if (NC.route() !== "#/" && v) v(); };
  document.addEventListener("nc:lang", rerender);
  document.addEventListener("nc:auth", rerender);
})();
