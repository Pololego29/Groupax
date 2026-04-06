/**
 * app.js
 * Gère l'affichage des offres, les filtres, la pagination
 * et la communication avec l'API FastAPI.
 */

const API = "http://localhost:8000/api";
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
  const data = await fetchJson(`${API}/stats`);
  if (!data) return;

  document.getElementById("stat-total").textContent = data.total.toLocaleString("fr-FR");

  // Badge par source
  const sourcesEl = document.getElementById("stat-sources");
  sourcesEl.innerHTML = Object.entries(data.by_source)
    .map(([src, count]) => `
      <div>
        <span class="opacity-70 capitalize">${src}</span>
        <span class="ml-1 font-semibold">${count.toLocaleString("fr-FR")}</span>
      </div>
    `).join("");

  // Dernière collecte
  const raw = data.last_scrape;
  const lastEl = document.getElementById("stat-last");
  if (raw && raw !== "Jamais") {
    const d = new Date(raw);
    lastEl.textContent = d.toLocaleString("fr-FR", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"
    });
  } else {
    lastEl.textContent = "Jamais";
  }
}

// =============================================================================
// SOURCES (pour le select)
// =============================================================================

async function loadSources() {
  const sources = await fetchJson(`${API}/sources`);
  if (!sources) return;

  const select = document.getElementById("source");
  sources.forEach(src => {
    const opt = document.createElement("option");
    opt.value = src;
    opt.textContent = src.charAt(0).toUpperCase() + src.slice(1);
    select.appendChild(opt);
  });
}

// =============================================================================
// OFFRES
// =============================================================================

async function loadOffers(page = 1) {
  currentPage = page;
  showLoading(true);

  const search   = document.getElementById("search").value.trim();
  const location = document.getElementById("location").value.trim();
  const source   = document.getElementById("source").value;

  const params = new URLSearchParams({ page, per_page: 20 });
  if (search)   params.set("search", search);
  if (location) params.set("location", location);
  if (source)   params.set("source", source);

  const data = await fetchJson(`${API}/offres?${params}`);
  showLoading(false);

  if (!data) return;

  const grid  = document.getElementById("offers-grid");
  const empty = document.getElementById("empty-state");
  const count = document.getElementById("result-count");

  if (data.offers.length === 0) {
    grid.innerHTML = "";
    empty.classList.remove("hidden");
    count.textContent = "";
  } else {
    empty.classList.add("hidden");
    count.textContent = `${data.total.toLocaleString("fr-FR")} offres trouvées`;
    grid.innerHTML = data.offers.map(renderCard).join("");
  }

  renderPagination(data.page, data.pages);
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

async function triggerScrape() {
  showToast("Scraping lancé, les offres seront mises à jour dans quelques minutes…");
  await fetch(`${API}/scrape`, { method: "POST" });
  setTimeout(() => { loadStats(); loadOffers(currentPage); }, 3000);
}

// =============================================================================
// UTILITAIRES
// =============================================================================

async function fetchJson(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.error("Erreur API :", e);
    return null;
  }
}

function showLoading(show) {
  document.getElementById("loading").classList.toggle("hidden", !show);
  document.getElementById("offers-grid").classList.toggle("hidden", show);
}

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
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
