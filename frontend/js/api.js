const API_BASE = "/api";

const Auth = {
  get accessToken()  { return localStorage.getItem("sw_access");  },
  get refreshToken() { return localStorage.getItem("sw_refresh"); },
  get user()         { return JSON.parse(localStorage.getItem("sw_user") || "null"); },

  save(access, refresh, user) {
    localStorage.setItem("sw_access",  access);
    localStorage.setItem("sw_refresh", refresh);
    localStorage.setItem("sw_user", JSON.stringify(user));
  },
  clear() {
    ["sw_access","sw_refresh","sw_user"].forEach(k => localStorage.removeItem(k));
  },
  isLoggedIn() { return !!this.accessToken; },
};

const Toast = (() => {
  let container;

  function ensureContainer() {
    if (!container) {
      container = document.createElement("div");
      container.id = "toast-container";
      container.style.cssText = `
        position:fixed; bottom:24px; right:24px; z-index:9999;
        display:flex; flex-direction:column; gap:10px; pointer-events:none;
      `;
      document.body.appendChild(container);
    }
  }

  function show(message, type = "info", duration = 4000) {
    ensureContainer();
    const colors = {
      success: { bg: "#dcfce7", border: "#15803d", text: "#15803d", icon: "✓" },
      error:   { bg: "#fee2e2", border: "#b91c1c", text: "#b91c1c", icon: "✕" },
      warning: { bg: "#fef3c7", border: "#b45309", text: "#b45309", icon: "⚠" },
      info:    { bg: "#dbeafe", border: "#1d4ed8", text: "#1d4ed8", icon: "ℹ" },
    };
    const c = colors[type] || colors.info;
    const toast = document.createElement("div");
    toast.style.cssText = `
      background:${c.bg}; border:1px solid ${c.border}; color:${c.text};
      padding:12px 16px; border-radius:8px; font-size:13px; font-family:'Inter',sans-serif;
      max-width:320px; box-shadow:0 4px 12px rgba(0,0,0,.1);
      display:flex; align-items:flex-start; gap:8px; pointer-events:all;
      animation:swToastIn .25s ease; cursor:pointer;
    `;
    toast.innerHTML = `<span style="font-weight:700;flex-shrink:0">${c.icon}</span><span>${message}</span>`;
    toast.onclick = () => dismiss(toast);

    if (!document.getElementById("sw-toast-style")) {
      const style = document.createElement("style");
      style.id = "sw-toast-style";
      style.textContent = `
        @keyframes swToastIn  { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:none} }
        @keyframes swToastOut { from{opacity:1} to{opacity:0;transform:translateY(4px)} }
      `;
      document.head.appendChild(style);
    }

    container.appendChild(toast);
    setTimeout(() => dismiss(toast), duration);
  }

  function dismiss(toast) {
    toast.style.animation = "swToastOut .2s ease forwards";
    setTimeout(() => toast.remove(), 200);
  }

  return { show, success: m => show(m,"success"), error: m => show(m,"error",6000),
           warning: m => show(m,"warning"), info: m => show(m,"info") };
})();

const Loading = {
  _count: 0,
  _bar: null,

  start() {
    this._count++;
    if (!this._bar) {
      this._bar = document.createElement("div");
      this._bar.id = "sw-progress-bar";
      this._bar.style.cssText = `
        position:fixed; top:0; left:0; height:2px; width:0%; z-index:10000;
        background:linear-gradient(90deg,#4f46e5,#f97316);
        transition:width .3s ease; pointer-events:none;
      `;
      document.body.appendChild(this._bar);
    }
    this._bar.style.width = "40%";
  },

  done() {
    this._count = Math.max(0, this._count - 1);
    if (this._count === 0 && this._bar) {
      this._bar.style.width = "100%";
      setTimeout(() => {
        if (this._bar) { this._bar.style.opacity = "0"; }
        setTimeout(() => {
          if (this._bar) { this._bar.remove(); this._bar = null; }
        }, 300);
      }, 300);
    }
  },

  setButton(btn, loading, originalText) {
    if (loading) {
      btn.disabled = true;
      btn.dataset.origText = btn.innerHTML;
      btn.innerHTML = `<span class="spinner" style="display:inline-block;width:12px;height:12px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite;margin-right:6px;vertical-align:middle;"></span>Loading…`;
    } else {
      btn.disabled = false;
      btn.innerHTML = btn.dataset.origText || originalText || "Submit";
    }
  },
};

async function apiFetch(path, options = {}) {
  Loading.start();
  const headers = { "Content-Type": "application/json", ...options.headers };

  if (Auth.accessToken) {
    headers["Authorization"] = `Bearer ${Auth.accessToken}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch (err) {
    Loading.done();
    Toast.error("Network error — is the server running?");
    throw err;
  }

  if (response.status === 401 && Auth.refreshToken && !options._retry) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return apiFetch(path, { ...options, _retry: true });
    } else {
      Auth.clear();
      window.location.href = "login.html";
      Loading.done();
      return null;
    }
  }

  Loading.done();
  const data = await response.json().catch(() => ({}));

  if (!response.ok && !options.silent) {
    const msg = data.error || `Request failed (${response.status})`;
    Toast.error(msg);
  }

  return { ok: response.ok, status: response.status, data };
}

async function tryRefresh() {
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${Auth.refreshToken}`,
      },
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem("sw_access", data.data.access_token);
      return true;
    }
  } catch (_) {}
  return false;
}

const API = {
  auth: {
    login:   (email, password) => apiFetch("/auth/login",   { method:"POST", body: JSON.stringify({email, password}) }),
    logout:  ()                => apiFetch("/auth/logout",  { method:"POST" }),
    me:      ()                => apiFetch("/auth/me"),
  },
  inventory: {
    list:    (params={}) => apiFetch("/inventory?" + new URLSearchParams(params)),
    adjust:  (body)      => apiFetch("/inventory/adjust",   { method:"POST", body: JSON.stringify(body) }),
    transfer:(body)      => apiFetch("/inventory/transfer", { method:"POST", body: JSON.stringify(body) }),
    movements:(params={})=> apiFetch("/inventory/movements?" + new URLSearchParams(params)),
    lowStock:(params={}) => apiFetch("/inventory/low-stock?" + new URLSearchParams(params)),
    predict: (params={}) => apiFetch("/inventory/predict-stockout?" + new URLSearchParams(params)),
  },
  products: {
    list:    (params={}) => apiFetch("/products?" + new URLSearchParams(params)),
    get:     (id)        => apiFetch(`/products/${id}`),
    barcode: (bc)        => apiFetch(`/products/barcode/${bc}`),
    create:  (body)      => apiFetch("/products",    { method:"POST",   body: JSON.stringify(body) }),
    update:  (id, body)  => apiFetch(`/products/${id}`, { method:"PUT", body: JSON.stringify(body) }),
    delete:  (id)        => apiFetch(`/products/${id}`, { method:"DELETE" }),
    restore: (id)        => apiFetch(`/products/${id}/restore`, { method:"POST" }),
  },
  orders: {
    list:    (params={}) => apiFetch("/orders?" + new URLSearchParams(params)),
    get:     (id)        => apiFetch(`/orders/${id}`),
    create:  (body)      => apiFetch("/orders",        { method:"POST", body: JSON.stringify(body) }),
    approve: (id)        => apiFetch(`/orders/${id}/approve`, { method:"POST" }),
    cancel:  (id, reason)=> apiFetch(`/orders/${id}/cancel`,  { method:"POST", body: JSON.stringify({reason}) }),
  },
  shipments: {
    list:    (params={}) => apiFetch("/shipments?" + new URLSearchParams(params)),
    get:     (id)        => apiFetch(`/shipments/${id}`),
    create:  (body)      => apiFetch("/shipments",     { method:"POST", body: JSON.stringify(body) }),
    status:  (id, status, notes)=> apiFetch(`/shipments/${id}/status`, { method:"PATCH", body: JSON.stringify({status, notes}) }),
  },
  suppliers: {
    list:    (params={}) => apiFetch("/suppliers?" + new URLSearchParams(params)),
    create:  (body)      => apiFetch("/suppliers",     { method:"POST", body: JSON.stringify(body) }),
    update:  (id, body)  => apiFetch(`/suppliers/${id}`, { method:"PUT", body: JSON.stringify(body) }),
    pos:     (params={}) => apiFetch("/suppliers/purchase-orders?" + new URLSearchParams(params)),
    createPO:(body)      => apiFetch("/suppliers/purchase-orders", { method:"POST", body: JSON.stringify(body) }),
    receivePO:(id, body) => apiFetch(`/suppliers/purchase-orders/${id}/receive`, { method:"POST", body: JSON.stringify(body) }),
    performance:(id)     => apiFetch(`/suppliers/${id}/performance`),
  },
  warehouses: {
    list:  () => apiFetch("/warehouses"),
    create:(body) => apiFetch("/warehouses", { method:"POST", body: JSON.stringify(body) }),
  },
  notifications: {
    list:    (params={}) => apiFetch("/notifications?" + new URLSearchParams(params)),
    markRead:(id)        => apiFetch(`/notifications/${id}/read`, { method:"POST" }),
    markAll: ()          => apiFetch("/notifications/read-all",    { method:"POST" }),
  },
  reports: {
    kpis:        ()      => apiFetch("/reports/kpis"),
    inventoryCSV:()      => window.open(`${API_BASE}/reports/inventory/csv?token=${Auth.accessToken}`),
    inventoryPDF:()      => window.open(`${API_BASE}/reports/inventory/pdf?token=${Auth.accessToken}`),
    ordersPDF:   ()      => window.open(`${API_BASE}/reports/orders/pdf?token=${Auth.accessToken}`),
    ordersCSV:   ()      => window.open(`${API_BASE}/reports/orders/csv?token=${Auth.accessToken}`),
    suppliersPDF:()      => window.open(`${API_BASE}/reports/suppliers/pdf?token=${Auth.accessToken}`),
    auditCSV:    ()      => window.open(`${API_BASE}/reports/audit/csv?token=${Auth.accessToken}`),
  },
};

const RealtimeNotifications = (() => {
  let socket = null;

  function connect() {
    if (!Auth.accessToken) return;

    if (typeof io === "undefined") return;

    socket = io("http://localhost:5000", {
      auth: { token: Auth.accessToken },
      transports: ["websocket"],
    });

    socket.on("connect", () => {
      console.log("[WS] Connected");
    });

    socket.on("notification", (n) => {

      const type = { success:"success", warning:"warning", danger:"error", info:"info" }[n.severity] || "info";
      Toast.show(n.message || n.title, type);

      const badge = document.querySelector(".notif-badge");
      if (badge) {
        const count = parseInt(badge.textContent || "0") + 1;
        badge.textContent = count;
        badge.style.display = "inline-block";
      }

      if (typeof onRealtimeNotification === "function") onRealtimeNotification(n);
    });

    socket.on("unread_count", ({ count }) => {
      const badge = document.querySelector(".notif-badge");
      if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? "inline-block" : "none";
      }
    });

    socket.on("disconnect", () => console.log("[WS] Disconnected"));
  }

  function disconnect() {
    if (socket) { socket.disconnect(); socket = null; }
  }

  return { connect, disconnect };
})();

const Validate = {

  form(formEl) {
    let valid = true;
    formEl.querySelectorAll("[data-required]").forEach(input => {
      const val = input.value.trim();
      const errEl = formEl.querySelector(`[data-error="${input.name || input.id}"]`);
      if (!val) {
        valid = false;
        input.style.borderColor = "var(--danger)";
        if (errEl) { errEl.textContent = input.dataset.required; errEl.style.display = "block"; }
      } else {
        input.style.borderColor = "";
        if (errEl) { errEl.style.display = "none"; }
      }
    });

    formEl.querySelectorAll('input[type="email"]').forEach(input => {
      if (input.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value)) {
        valid = false;
        input.style.borderColor = "var(--danger)";
      }
    });

    formEl.querySelectorAll('input[type="number"][min]').forEach(input => {
      const min = parseFloat(input.min);
      if (input.value !== "" && parseFloat(input.value) < min) {
        valid = false;
        input.style.borderColor = "var(--danger)";
        const errEl = formEl.querySelector(`[data-error="${input.name || input.id}"]`);
        if (errEl) { errEl.textContent = `Must be ≥ ${min}`; errEl.style.display = "block"; }
      }
    });

    return valid;
  },

  field(input, message) {
    input.style.borderColor = "var(--danger)";
    const errEl = document.querySelector(`[data-error="${input.name || input.id}"]`);
    if (errEl) { errEl.textContent = message; errEl.style.display = "block"; }
  },

  clear(formEl) {
    formEl.querySelectorAll("input,select,textarea").forEach(el => el.style.borderColor = "");
    formEl.querySelectorAll("[data-error]").forEach(el => el.style.display = "none");
  },
};

function debounce(fn, delay = 350) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

function renderPagination(container, { page, pages, total, per_page }, onPageChange) {
  if (!container) return;
  const start = (page - 1) * per_page + 1;
  const end   = Math.min(page * per_page, total);

  container.innerHTML = `
    <span class="text-muted" style="font-size:12px;">Showing ${start}–${end} of ${total}</span>
    <div class="spacer"></div>
    ${page > 1 ? `<button class="btn btn--ghost pag-btn" data-page="${page-1}">‹ Prev</button>` : ""}
    ${Array.from({length: Math.min(pages, 5)}, (_,i) => {
      const p = i + 1;
      return `<button class="btn ${p===page?'btn--secondary':'btn--ghost'} pag-btn" data-page="${p}">${p}</button>`;
    }).join("")}
    ${pages > 5 && page < pages ? `<span class="text-faint">…</span><button class="btn btn--ghost pag-btn" data-page="${pages}">${pages}</button>` : ""}
    ${page < pages ? `<button class="btn btn--ghost pag-btn" data-page="${page+1}">Next ›</button>` : ""}
  `;
  container.querySelectorAll(".pag-btn").forEach(btn => {
    btn.onclick = () => onPageChange(parseInt(btn.dataset.page));
  });
}

function requireAuth() {
  if (!Auth.isLoggedIn()) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

function populateSidebarUser() {
  const user = Auth.user;
  if (!user) return;
  const nameEl = document.querySelector(".user-name");
  const roleEl = document.querySelector(".user-role");
  const avEl   = document.querySelector(".user-avatar");
  if (nameEl) nameEl.textContent = user.full_name;
  if (roleEl) roleEl.textContent = user.role ? (user.role.charAt(0).toUpperCase() + user.role.slice(1)) : "";
  if (avEl) avEl.textContent = (user.full_name || "?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase();
}

function logout() {
  API.auth.logout().finally(() => {
    Auth.clear();
    RealtimeNotifications.disconnect();
    window.location.href = "login.html";
  });
}

function initTheme() {
  const saved = localStorage.getItem("sw_theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "dark";
  const next = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("sw_theme", next);

  document.querySelectorAll(".theme-toggle-knob").forEach(knob => {
    knob.textContent = next === "dark" ? "🌙" : "☀";
  });
}

initTheme();

window.Auth   = Auth;
window.API    = API;
window.Toast  = Toast;
window.Loading= Loading;
window.Validate=Validate;
window.debounce=debounce;
window.renderPagination=renderPagination;
window.requireAuth=requireAuth;
window.populateSidebarUser=populateSidebarUser;
window.logout = logout;
window.RealtimeNotifications = RealtimeNotifications;
window.toggleTheme = toggleTheme;
window.initTheme = initTheme;
