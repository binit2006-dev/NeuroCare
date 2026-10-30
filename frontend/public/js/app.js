/* NeuroCare core: helpers, language, auth, header, routing */
const NC = (window.NC = {});

NC.$ = (sel, root = document) => root.querySelector(sel);
NC.$$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
NC.esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
NC.icons = () => window.lucide && window.lucide.createIcons();

NC.api = async (path, options = {}) => {
  const res = await fetch(`/api${path}`, { credentials: "same-origin", ...options });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.detail || `Request failed (${res.status})`), { status: res.status });
  return data;
};

NC.toast = (msg, kind = "info") => {
  const el = NC.$("#toast");
  el.textContent = msg;
  el.className = `toast show ${kind}`;
  clearTimeout(NC._toastTimer);
  NC._toastTimer = setTimeout(() => (el.className = "toast"), 3800);
};

/* ---------- Language ---------- */
NC.lang = localStorage.getItem("neurocare_lang") || "en";
NC.t = (key, vars) => {
  let s = window.TRANSLATIONS[NC.lang]?.[key] ?? window.TRANSLATIONS.en[key] ?? key;
  if (vars) Object.entries(vars).forEach(([k, v]) => (s = s.replace(`{${k}}`, v)));
  return s;
};
NC.applyLang = () => {
  document.documentElement.lang = NC.lang;
  NC.$$("[data-i18n]").forEach((el) => (el.textContent = NC.t(el.dataset.i18n)));
  NC.$$("[data-i18n-placeholder]").forEach((el) => (el.placeholder = NC.t(el.dataset.i18nPlaceholder)));
  NC.$(".lang-toggle").setAttribute("aria-label", NC.t("lang_switch_aria"));
};
NC.setLang = (lang) => {
  NC.lang = lang;
  localStorage.setItem("neurocare_lang", lang);
  NC.applyLang();
  NC.renderNav();
  NC.renderUser();
  document.dispatchEvent(new CustomEvent("nc:lang"));
};

/* ---------- Header ---------- */
const NAV = [
  { hash: "#/", key: "nav_scan", id: "scan" },
  { hash: "#/history", key: "nav_history", id: "my-scans" },
  { hash: "#/about", key: "nav_about", id: "about-pinn" },
  { hash: "#/downloads", key: "nav_downloads", id: "downloads" },
];
NC.renderNav = () => {
  const current = NC.route();
  NC.$$("[data-nav]").forEach((nav) => {
    const prefix = nav.dataset.nav;
    nav.innerHTML = NAV.map(
      (n) => `<a href="${n.hash}" data-testid="${prefix}-${n.id}" class="${current === n.hash ? "active" : ""}">${NC.esc(NC.t(n.key))}</a>`
    ).join("");
  });
};

/* ---------- Auth (Emergent-managed Google sign-in) ---------- */
NC.user = null;
NC.authReady = false;
NC.login = () => {
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const redirectUrl = window.location.origin + "/";
  window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
};
NC.logout = async () => {
  try { await NC.api("/auth/logout", { method: "POST" }); } catch (_) { /* already signed out */ }
  NC.user = null;
  NC.renderUser();
  document.dispatchEvent(new CustomEvent("nc:auth"));
};
NC.renderUser = () => {
  const box = NC.$("#user-menu");
  if (!NC.authReady) { box.innerHTML = ""; return; }
  if (!NC.user) {
    box.innerHTML = `<button class="btn btn-primary btn-sm" data-testid="google-signin-button" type="button"><i data-lucide="log-in"></i>${NC.esc(NC.t("sign_in"))}</button>`;
    box.firstElementChild.onclick = NC.login;
  } else {
    const avatar = NC.user.picture
      ? `<img class="avatar" data-testid="user-avatar" src="${NC.esc(NC.user.picture)}" alt="${NC.esc(NC.user.name)}" referrerpolicy="no-referrer" />`
      : `<span class="avatar" data-testid="user-avatar">${NC.esc((NC.user.name || "?")[0])}</span>`;
    box.innerHTML = `${avatar}<button class="icon-btn" data-testid="logout-button" type="button" aria-label="${NC.esc(NC.t("sign_out"))}"><i data-lucide="log-out"></i></button>`;
    box.querySelector("[data-testid=logout-button]").onclick = NC.logout;
  }
  NC.icons();
};
NC.initAuth = async () => {
  const match = window.location.hash.match(/session_id=([^&]+)/);
  if (match) {
    history.replaceState(null, "", window.location.pathname + "#/history");
    try {
      NC.user = await NC.api("/auth/session", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: match[1] }),
      });
      NC.toast(NC.t("welcome", { name: NC.user.name.split(" ")[0] }), "success");
    } catch (_) {
      NC.toast(NC.t("signin_failed"), "error");
      history.replaceState(null, "", window.location.pathname + "#/");
    }
  } else {
    try { NC.user = await NC.api("/auth/me"); } catch (_) { NC.user = null; }
  }
  NC.authReady = true;
  NC.renderUser();
  document.dispatchEvent(new CustomEvent("nc:auth"));
};

/* ---------- Router ---------- */
NC.views = {};
NC.route = () => {
  const h = window.location.hash.split("?")[0];
  return NAV.some((n) => n.hash === h) ? h : "#/";
};
NC.showView = (id, { scroll = true } = {}) => {
  NC.$$(".view").forEach((v) => (v.hidden = v.id !== id));
  if (scroll) window.scrollTo({ top: 0 });
};
NC.onRoute = () => {
  if (window.location.hash.includes("session_id=")) return;
  const r = NC.route();
  NC.renderNav();
  const handler = NC.views[r];
  if (handler) handler();
};

document.addEventListener("DOMContentLoaded", () => {
  NC.$("#year").textContent = new Date().getFullYear();
  NC.$(".lang-toggle").onclick = () => NC.setLang(NC.lang === "en" ? "hi" : "en");
  NC.applyLang();
  NC.renderNav();
  NC.icons();
  window.addEventListener("hashchange", NC.onRoute);
  const fromCallback = window.location.hash.includes("session_id=");
  NC.initAuth().then(() => fromCallback && NC.onRoute());
  if (!fromCallback) NC.onRoute();
});
