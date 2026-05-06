/**
 * app.js
 * Gère l'affichage des offres, les filtres, la pagination
 * et la communication avec l'API FastAPI.
 */

const API = typeof API_URL !== "undefined" ? API_URL : "http://localhost:8000/api";
let currentPage = 1;
let debounceTimer = null;

// =============================================================================
// INITIALISATION
// =============================================================================

document.addEventListener("DOMContentLoaded", () => {
  loadStats();
  loadSources();
  loadOffers(1);
});

// =============================================================================
// STATS
// =============================================================================

async function loadStats() {
  try {
    const data = await fetchJson(`${API}/stats`);
    if (!data) {
      console.warn("Failed to load stats");
      return;
    }

    const totalEl = document.getElementById("stat-total");
    if (totalEl) {
      totalEl.textContent = (data.total || 0).toLocaleString("fr-FR");
    }

    // Badge par source
    const sourcesEl = document.getElementById("stat-sources");
    if (sourcesEl) {
      sourcesEl.innerHTML = Object.entries(data.by_source || {})
        .map(([src, count]) => `
          <div>
            <span class="opacity-70 capitalize">${escapeHtml(src)}</span>
            <span class="ml-1 font-semibold">${(count || 0).toLocaleString("fr-FR")}</span>
          </div>
        `).join("");
    }

    // Dernière collecte
    const lastEl = document.getElementById("stat-last");
    if (lastEl) {
      const raw = data.last_scrape || "Jamais";
      if (raw && raw !== "Jamais") {
        try {
          const d = new Date(raw);
          lastEl.textContent = d.toLocaleString("fr-FR", {
            day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
          });
        } catch (e) {
          lastEl.textContent = raw;
        }
      } else {
        lastEl.textContent = "Jamais";
      }
    }
  } catch (e) {
    console.error("Error loading stats:", e);
  }
}

// =============================================================================
// SOURCES (pour le select)
// =============================================================================

async function loadSources() {
  try {
    const sources = await fetchJson(`${API}/sources`);
    if (!sources || !Array.isArray(sources)) {
      console.warn("No sources data received");
      return;
    }

    const select = document.getElementById("source");
    if (!select) return;
    
    sources.forEach(src => {
      const opt = document.createElement("option");
      opt.value = src;
      opt.textContent = src.charAt(0).toUpperCase() + src.slice(1);
      select.appendChild(opt);
    });
  } catch (e) {
    console.error("Error loading sources:", e);
  }
}

// =============================================================================
// OFFRES
// =============================================================================

async function loadOffers(page = 1) {
  try {
    currentPage = page;
    showLoading(true);

    const search   = (document.getElementById("search")?.value || "").trim();
    const location = (document.getElementById("location")?.value || "").trim();
    const source   = document.getElementById("source")?.value || "";

    const params = new URLSearchParams({ page, per_page: 20 });
    if (search)   params.set("search", search);
    if (location) params.set("location", location);
    if (source)   params.set("source", source);

    const data = await fetchJson(`${API}/offres?${params}`);
    showLoading(false);

    if (!data) {
      showToast("Erreur lors du chargement des offres");
      renderOffers([]);
      return;
    }

    renderOffers(data.offers || []);
    renderPagination(data.page || 1, data.pages || 0);

  } catch (e) {
    console.error("Error loading offers:", e);
    showLoading(false);
    showToast("Erreur de chargement");
    renderOffers([]);
  }
}

function renderOffers(offers) {
  const grid  = document.getElementById("offers-grid");
  const empty = document.getElementById("empty-state");
  const count = document.getElementById("result-count");

  if (!grid) return;

  if (!offers || offers.length === 0) {
    grid.innerHTML = "";
    if (empty) empty.classList.remove("hidden");
    if (count) count.textContent = "";
  } else {
    if (empty) empty.classList.add("hidden");
    if (count) count.textContent = `${offers.length} offres trouvées`;
    grid.innerHTML = offers.map(renderCard).join("");
  }
}

// =============================================================================
// RENDU D'UNE CARTE
// =============================================================================

function renderCard(offer) {
  const salary = offer.salary
    ? `<span>💰 ${offer.salary}</span>`
    : "";

  const date = offer.scraped_at
    ? `<span>🕐 ${formatDate(offer.scraped_at)}</span>`
    : "";

  const desc = offer.description
    ? `<p class="offer-description">${escapeHtml(offer.description)}</p>`
    : "";

  return `
    <div class="offer-card">
      <div>
        <p class="offer-title">${escapeHtml(offer.title)}</p>
        <p class="offer-company">${escapeHtml(offer.company || "Entreprise non précisée")}</p>
      </div>
      <div class="offer-meta">
        ${offer.location ? `<span>📍 ${escapeHtml(offer.location)}</span>` : ""}
        ${salary}
        ${date}
      </div>
      ${desc}
      <div class="offer-footer">
        <span class="source-badge">${offer.source}</span>
        ${offer.url
          ? `<a href="${offer.url}" target="_blank" rel="noopener" class="offer-link">Voir l'offre →</a>`
          : ""}
      </div>
    </div>
  `;
}

// =============================================================================
// PAGINATION
// =============================================================================

function renderPagination(page, totalPages) {
  const el = document.getElementById("pagination");
  if (totalPages <= 1) { el.innerHTML = ""; return; }

  const buttons = [];

  // Précédent
  if (page > 1) {
    buttons.push(btn("←", page - 1));
  }

  // Pages autour de la page courante
  const range = pagesRange(page, totalPages);
  range.forEach(p => {
    if (p === "...") {
      buttons.push(`<span class="px-2 text-gray-400">…</span>`);
    } else {
      buttons.push(btn(p, p, p === page));
    }
  });

  // Suivant
  if (page < totalPages) {
    buttons.push(btn("→", page + 1));
  }

  el.innerHTML = buttons.join("");
}

function btn(label, page, active = false) {
  return `<button class="page-btn ${active ? "active" : ""}" onclick="loadOffers(${page})">${label}</button>`;
}

function pagesRange(current, total) {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  if (current <= 4) return [1, 2, 3, 4, 5, "...", total];
  if (current >= total - 3) return [1, "...", total-4, total-3, total-2, total-1, total];
  return [1, "...", current-1, current, current+1, "...", total];
}

// =============================================================================
// ACTIONS
// =============================================================================

function debouncedSearch() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => loadOffers(1), 400);
}

function resetFilters() {
  document.getElementById("search").value = "";
  document.getElementById("location").value = "";
  document.getElementById("source").value = "";
  loadOffers(1);
}

function refresh() {
  loadStats();
  loadSources();
  loadOffers(currentPage);
  showToast("Données actualisées");
}

// =============================================================================
// UTILITAIRES
// =============================================================================

async function fetchJson(url) {
  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      timeout: 10000
    });
    if (!res.ok) {
      console.error(`HTTP Error ${res.status}: ${res.statusText}`);
      return null;
    }
    return await res.json();
  } catch (e) {
    console.error("API Error:", e);
    showToast("Erreur de connexion à l'API");
    return null;
  }
}

function showLoading(show) {
  const loading = document.getElementById("loading");
  const grid = document.getElementById("offers-grid");
  if (loading) loading.classList.toggle("hidden", !show);
  if (grid) grid.classList.toggle("hidden", show);
}

function formatDate(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
  } catch (e) {
    console.error("Date format error:", e);
    return iso;
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}

function showToast(msg) {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 4000);
}
