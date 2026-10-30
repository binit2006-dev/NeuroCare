/* NeuroCare scan flow: upload -> PINN prediction -> heatmap -> AI advice */
(() => {
  const { $, esc, t, api, toast, icons } = NC;
  const state = { file: null, preview: null, scan: null, advice: null, adviceError: null, loadingAdvice: false, reqId: 0 };

  /* ---------- Uploader ---------- */
  function pick(file) {
    if (!file) return;
    if (!file.type.startsWith("image/")) return toast(t("up_invalid"), "error");
    if (state.preview) URL.revokeObjectURL(state.preview);
    state.file = file;
    state.preview = URL.createObjectURL(file);
    $("#preview-img").src = state.preview;
    $("#file-name").textContent = file.name;
    $("#drop-empty").hidden = true;
    $("#drop-preview").hidden = false;
    $("#analyze-button").disabled = false;
  }

  function clearFile() {
    state.file = null;
    $("#file-input").value = "";
    $("#drop-empty").hidden = false;
    $("#drop-preview").hidden = true;
    $("#analyze-button").disabled = true;
  }

  async function analyze() {
    if (!state.file) return toast(t("up_missing"), "error");
    const fd = new FormData();
    fd.append("mri", state.file);
    fd.append("location", $("#location-input").value.trim());
    NC.showView("view-loading");
    try {
      state.scan = await api("/predict", { method: "POST", body: fd });
      state.advice = null;
      renderResults();
      loadAdvice();
    } catch (err) {
      toast(err.message || t("up_failed"), "error");
      NC.showView("view-home");
    }
  }

  /* ---------- Results ---------- */
  const pct = (v) => `${(v * 100).toFixed(1)}%`;

  function verdictCard(s) {
    const probs = Object.entries(s.class_probabilities)
      .map(([k, v]) => `
        <div class="prob" data-testid="prob-${k}">
          <div class="xs muted">${esc(t(`class_${k}`))}</div>
          <div class="strong">${pct(v)}</div>
          <div class="bar"><span style="width:${v * 100}%"></span></div>
        </div>`).join("");
    const demo = s.demo_mode
      ? `<div class="banner" data-testid="demo-mode-banner"><i data-lucide="info"></i>${esc(t("demo_1"))} <code>backend/models/</code> ${esc(t("demo_2"))}</div>` : "";
    return `${demo}
      <div class="verdict ${s.tumor_detected ? "warm" : "calm"} reveal">
        <p class="eyebrow-sm"><i data-lucide="${s.tumor_detected ? "info" : "check-circle-2"}"></i>${esc(t("res_label"))}</p>
        <h2 class="display-sm" data-testid="result-verdict">${esc(t(`label_${s.tumor_type}`))}</h2>
        <div class="meta-row">
          <div><div class="muted small">${esc(t("res_confidence"))}</div><div class="strong big">${pct(s.confidence)}</div></div>
          <div class="sep"></div>
          <div><div class="muted small">${esc(t("res_file"))}</div><div class="strong trunc">${esc(s.filename)}</div></div>
          <div class="sep hide-sm"></div>
          <div class="hide-sm"><div class="muted small">${esc(t("res_location"))}</div><div class="strong">${esc(s.location || "—")}</div></div>
          <button class="btn btn-ghost btn-sm push-right" data-testid="reset-button" id="reset-button" type="button"><i data-lucide="refresh-ccw"></i>${esc(t("res_new_scan"))}</button>
        </div>
        <div class="prob-grid">${probs}</div>
      </div>`;
  }

  function heatmapCard(s) {
    if (!s.heatmap || !state.preview) return "";
    const area = s.tumor_area_pct || 0;
    const yes = area > 0.05;
    return `
      <div class="card heatmap reveal" data-testid="heatmap-card">
        <div class="heat-frame">
          <img data-testid="heatmap-base-image" src="${state.preview}" alt="Uploaded MRI scan" />
          <img data-testid="heatmap-overlay" id="heatmap-overlay" class="heat-glow" src="${s.heatmap}" alt="Predicted tumor region" />
        </div>
        <div>
          <p class="eyebrow"><i data-lucide="flame"></i>${esc(t("hm_small"))}</p>
          <h3 class="h3">${esc(t(yes ? "hm_title_yes" : "hm_title_no"))}</h3>
          <p class="small">${esc(t(yes ? "hm_desc_yes" : "hm_desc_no"))}</p>
          <div class="area-chip" data-testid="tumor-area-pct"><span>${area.toFixed(1)}%</span><small>${esc(t("hm_area"))}</small></div>
          <label class="row-between small">
            <span>${esc(t("hm_show"))}</span>
            <span class="switch"><input type="checkbox" id="heatmap-toggle" data-testid="heatmap-toggle" checked /><i></i></span>
          </label>
          <label class="small block mt">
            <span class="row-between"><span>${esc(t("hm_intensity"))}</span><span class="muted" id="opacity-value">85%</span></span>
            <input type="range" id="heatmap-opacity-slider" data-testid="heatmap-opacity-slider" min="10" max="100" step="5" value="85" />
          </label>
        </div>
      </div>`;
  }

  const list = (items, cls = "") => (items || []).map((x) => `<li class="${cls}">${esc(x)}</li>`).join("");
  const telHref = (n) => String(n || "").replace(/[^\d+]/g, "");

  function adviceSection(a) {
    if (!a) return "";
    const info = a.tumor_info || {};
    const hospitals = (a.nearby_hospitals || []).map((h, i) => `
      <div class="hospital" data-testid="hospital-${i}">
        <div class="xs muted">${esc(h.city)}</div><div class="strong">${esc(h.name)}</div>
        <div class="xs accent">${esc(h.specialty)}</div><div class="small muted mt-sm">${esc(h.notes)}</div>
      </div>`).join("");
    const contacts = (a.emergency_contacts || []).map((c, i) => `
      <a class="contact" href="tel:${esc(telHref(c.number))}" data-testid="emergency-contact-${i}"><span>${esc(c.label)}</span><strong>${esc(c.number)}</strong></a>`).join("");
    const specialists = (a.recommended_specialists || []).map((s) => `
      <div class="specialist"><div class="strong">${esc(s.role)}</div><div class="small muted">${esc(s.why)}</div></div>`).join("");
    const steps = (a.next_steps || []).map((n, i) => `<li><span class="num">${i + 1}</span><span>${esc(n)}</span></li>`).join("");
    const tips = (a.mindset_tips || []).map((x) => `<li><i data-lucide="sparkles"></i><span>${esc(x)}</span></li>`).join("");
    const location = state.scan.location ? `<span class="small muted">${esc(t("based_on", { place: state.scan.location }))}</span>` : "";
    return `
      <div class="advice-grid ${state.loadingAdvice || state.adviceError ? "dim" : ""}" data-testid="advice-grid">
        <div class="card span-7" data-testid="tumor-info-card">
          <p class="eyebrow"><i data-lucide="info"></i>${esc(t("about_result"))}</p>
          <h3 class="h3">${esc(info.name)}</h3><p>${esc(info.overview)}</p>
          <div class="small muted strong mt">${esc(t("symptoms"))}</div>
          <ul class="dots-list">${list(info.common_symptoms)}</ul>
          ${info.severity_note ? `<div class="note mt">${esc(info.severity_note)}</div>` : ""}
        </div>
        <div class="card dark span-5" data-testid="emergency-card">
          <p class="eyebrow-sm light"><i data-lucide="phone"></i>${esc(t("emergency_small"))}</p>
          <h3 class="h3">${esc(t("emergency_title"))}</h3><div class="contacts">${contacts}</div>
        </div>
        <div class="card span-12" data-testid="hospitals-card">
          <div class="row-between wrap"><div><p class="eyebrow"><i data-lucide="hospital"></i>${esc(t("hospitals_small"))}</p>
          <h3 class="h3">${esc(t("hospitals_title"))}</h3></div>${location}</div>
          <div class="hospital-grid">${hospitals}</div>
        </div>
        <div class="card span-7" data-testid="specialists-card">
          <p class="eyebrow"><i data-lucide="user-round"></i>${esc(t("specialists_small"))}</p>${specialists}
        </div>
        <div class="card soft span-5" data-testid="next-steps-card">
          <p class="eyebrow"><i data-lucide="check-circle-2"></i>${esc(t("next_steps"))}</p><ol class="steps">${steps}</ol>
        </div>
        <div class="card split span-12" data-testid="mindset-card">
          <img class="split-img" src="https://images.unsplash.com/photo-1631217868264-e5b90bb7e133?crop=entropy&cs=srgb&fm=jpg&q=85&w=800" alt="A smiling doctor with a patient" />
          <div class="split-body"><p class="eyebrow">${esc(t("mindset_small"))}</p>
          <h3 class="h3">${esc(t("mindset_title"))}</h3><ul class="tips">${tips}</ul></div>
        </div>
        <p class="xs muted span-12" data-testid="disclaimer">${esc(a.disclaimer)}</p>
      </div>`;
  }

  function adviceStatus() {
    if (state.loadingAdvice) {
      return `<div class="advice-status" data-testid="advice-loading"><i data-lucide="sparkles" class="pulse"></i>${esc(t("advice_loading"))}</div>`;
    }
    if (state.adviceError) {
      return `<div class="error-box" data-testid="advice-error"><i data-lucide="alert-circle"></i><div>
        <div class="strong">${esc(t("advice_error_title"))}</div><div class="small muted">${esc(state.adviceError)}</div>
        <button class="btn btn-primary btn-sm mt" data-testid="retry-advice-button" id="retry-advice" type="button">${esc(t("retry"))}</button></div></div>`;
    }
    return "";
  }

  function renderResults() {
    const s = state.scan;
    const root = $("#results-root");
    const keepOpacity = $("#heatmap-opacity-slider")?.value;
    const keepShow = $("#heatmap-toggle")?.checked;
    root.innerHTML = verdictCard(s) + heatmapCard(s) + adviceStatus() + adviceSection(state.advice);
    NC.showView("view-results");
    window.scrollTo({ top: 0 });
    $("#reset-button").onclick = reset;
    $("#retry-advice") && ($("#retry-advice").onclick = loadAdvice);
    const slider = $("#heatmap-opacity-slider");
    if (slider) {
      if (keepOpacity) slider.value = keepOpacity;
      if (keepShow === false) $("#heatmap-toggle").checked = false;
      const sync = () => {
        $("#opacity-value").textContent = `${slider.value}%`;
        $("#heatmap-overlay").style.opacity = $("#heatmap-toggle").checked ? slider.value / 100 : 0;
        slider.disabled = !$("#heatmap-toggle").checked;
      };
      slider.oninput = sync;
      $("#heatmap-toggle").onchange = sync;
      sync();
    }
    icons();
  }

  async function loadAdvice() {
    const myId = ++state.reqId;
    const scan = state.scan;
    state.loadingAdvice = true;
    state.adviceError = null;
    renderResults();
    try {
      const data = await api("/advice", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scan_id: scan.id, language: NC.lang }),
      });
      if (myId !== state.reqId) return;
      state.advice = data;
    } catch (err) {
      if (myId !== state.reqId) return;
      state.adviceError = err.message || t("advice_error_fallback");
    }
    state.loadingAdvice = false;
    if (state.scan === scan && NC.route() === "#/") renderResults();
  }

  function reset() {
    state.reqId++;
    state.scan = null;
    state.advice = null;
    state.adviceError = null;
    clearFile();
    NC.showView("view-home");
    setTimeout(() => $("#scan").scrollIntoView({ behavior: "smooth" }), 50);
  }

  /* ---------- Wiring ---------- */
  NC.views["#/"] = () => (state.scan ? renderResults() : NC.showView("view-home"));

  document.addEventListener("nc:lang", () => {
    if (state.scan && NC.route() === "#/") loadAdvice();
  });

  document.addEventListener("DOMContentLoaded", () => {
    const dz = $("#dropzone");
    $("#file-input").onchange = (e) => pick(e.target.files[0]);
    dz.ondragover = (e) => { e.preventDefault(); dz.classList.add("over"); };
    dz.ondragleave = () => dz.classList.remove("over");
    dz.ondrop = (e) => { e.preventDefault(); dz.classList.remove("over"); pick(e.dataTransfer.files[0]); };
    $("#clear-file").onclick = (e) => { e.preventDefault(); e.stopPropagation(); clearFile(); };
    $("#analyze-button").onclick = analyze;
    $("#hero-cta").onclick = () => $("#scan").scrollIntoView({ behavior: "smooth" });
  });
})();
