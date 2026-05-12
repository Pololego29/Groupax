"""
scrapers/hellowork.py
=====================
Scraper HelloWork France pour les offres d'alternance.

Utilise Playwright (Chromium) car HelloWork charge ses offres via JavaScript.
Lancer via : python -m scrapers.run_scraper

Variables d'environnement :
    SCRAPER_QUERY       : Requête de recherche (défaut : "alternance")
    SCRAPER_LOCATION    : Localisation (défaut : "France")
    SCRAPER_MAX_PAGES   : Nombre de pages (défaut : 5)
    SCRAPER_HEADLESS    : true/false — headless mode (défaut : false en local)
"""

import asyncio
import os
import random
import re
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


# =============================================================================
# SECTION 1 – MODÈLE DE DONNÉES
# =============================================================================

@dataclass
class JobOffer:
    """Représente une offre d'alternance normalisée, quelle que soit la source."""
    title:         str
    company:       str
    location:      str
    contract_type: str
    salary:        str
    description:   str
    url:           str
    source:        str
    scraped_at:    str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# SECTION 2 – CONFIGURATION
# =============================================================================

def _env_str(key: str, default: str) -> str:
    val = os.getenv(key)
    return val if val else default


def _env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    try:
        return int(val) if val else default
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


BASE_URL  = "https://www.hellowork.com/fr-fr"
QUERY     = _env_str("SCRAPER_QUERY",    "alternance")
LOCATION  = _env_str("SCRAPER_LOCATION", "France")
MAX_PAGES = _env_int("SCRAPER_MAX_PAGES", 5)
MAX_RETRY = _env_int("SCRAPER_MAX_RETRY", 2)
HEADLESS  = _env_bool("SCRAPER_HEADLESS", False)

DELAY_MIN = 4.0
DELAY_MAX = 8.0

TIMEOUT_GOTO     = 60_000
TIMEOUT_SELECTOR = 30_000

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Sélecteurs HelloWork (à ajuster si le DOM change)
# Les cards d'offres sont dans des balises <li> avec un attribut data-id-offre
CARD_SELECTOR       = "li[data-id-offre]"
TITLE_SELECTOR      = "h2 a, h3 a"
COMPANY_SELECTOR    = "p[data-cy='company-name'], span[data-cy='company-name']"
LOCATION_SELECTOR   = "p[data-cy='job-location'], span[data-cy='job-location']"
SALARY_SELECTOR     = "p[data-cy='job-salary'], span[data-cy='job-salary']"
CONTRACT_SELECTOR   = "p[data-cy='job-contract'], span[data-cy='job-contract']"
DESC_SELECTOR       = "p[data-cy='job-description'], div[data-cy='job-description']"
LINK_SELECTOR       = "h2 a[href], h3 a[href]"
NEXT_PAGE_SELECTOR  = "a[aria-label='Page suivante'], a[rel='next'], button[aria-label='Page suivante']"


# =============================================================================
# SECTION 3 – FONCTIONS UTILITAIRES
# =============================================================================

def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


async def human_scroll(page, steps: int = 4) -> None:
    for _ in range(steps):
        await page.mouse.wheel(0, random.randint(300, 600))
        await asyncio.sleep(random.uniform(0.3, 0.8))


async def is_blocked(page) -> bool:
    title = await page.title()
    keywords = ["captcha", "robot", "vérification", "verification", "blocked", "access denied"]
    return any(k in title.lower() for k in keywords)


async def _get_text(el, attr: str | None = None) -> str:
    """Récupère le texte ou un attribut d'un élément, retourne '' si None."""
    if el is None:
        return ""
    try:
        if attr:
            return clean_text(await el.get_attribute(attr))
        return clean_text(await el.inner_text())
    except Exception:
        return ""


# =============================================================================
# SECTION 4 – EXTRACTION D'UNE PAGE
# =============================================================================

async def extract_offers_from_page(page) -> list[JobOffer]:
    offers = []

    cards = await page.query_selector_all(CARD_SELECTOR)

    if not cards:
        print("  [warn] Aucune card trouvée — sélecteurs à mettre à jour ou page bloquée")
        return offers

    for card in cards:
        try:
            title_el    = await card.query_selector(TITLE_SELECTOR)
            company_el  = await card.query_selector(COMPANY_SELECTOR)
            location_el = await card.query_selector(LOCATION_SELECTOR)
            salary_el   = await card.query_selector(SALARY_SELECTOR)
            contract_el = await card.query_selector(CONTRACT_SELECTOR)
            desc_el     = await card.query_selector(DESC_SELECTOR)
            link_el     = await card.query_selector(LINK_SELECTOR)

            title         = await _get_text(title_el)
            company       = await _get_text(company_el)
            location      = await _get_text(location_el)
            salary        = await _get_text(salary_el)
            contract_type = await _get_text(contract_el) or "Alternance"
            description   = await _get_text(desc_el)

            # Récupération de l'URL : href absolu ou relatif
            raw_href = await _get_text(link_el, attr="href") if link_el else ""
            if raw_href.startswith("http"):
                url = raw_href
            elif raw_href:
                url = f"https://www.hellowork.com{raw_href}"
            else:
                url = ""

            if not title:
                continue

            offers.append(JobOffer(
                title=title,
                company=company,
                location=location,
                contract_type=contract_type,
                salary=salary,
                description=description,
                url=url,
                source="hellowork",
            ))

        except Exception as e:
            print(f"  [warn] Erreur extraction card : {e}")
            continue

    return offers


# =============================================================================
# SECTION 5 – SCRAPER PRINCIPAL
# =============================================================================

class HelloWorkScraper:
    """
    Orchestre le scraping complet d'HelloWork sur plusieurs pages.

    Anti-détection : warm-up, scroll humain, rotation UA,
    navigation via bouton page suivante, délais aléatoires, retry.
    """

    def __init__(self, query: str = QUERY, location: str = LOCATION, max_pages: int = MAX_PAGES):
        self.query     = query
        self.location  = location
        self.max_pages = max_pages
        self.offers:     list[JobOffer] = []
        self._seen_urls: set[str]       = set()
        self.stats: dict = {
            "query":             query,
            "location":          location,
            "started_at":        None,
            "ended_at":          None,
            "duration_seconds":  0.0,
            "pages_scraped":     0,
            "pages_blocked":     0,
            "offers_total":      0,
            "offers_new":        0,
            "offers_duplicates": 0,
        }

    def _add_offers(self, new_offers: list[JobOffer]) -> int:
        """Filtre les doublons intra-session et ajoute les offres uniques."""
        added = 0
        for o in new_offers:
            key = o.url or f"{o.title}|{o.company}|{o.location}"
            if key in self._seen_urls:
                continue
            self._seen_urls.add(key)
            self.offers.append(o)
            added += 1
        self.stats["offers_new"]        += added
        self.stats["offers_duplicates"] += len(new_offers) - added
        self.stats["pages_scraped"]     += 1
        return added

    def _build_search_url(self, page_num: int = 1) -> str:
        """
        Construit l'URL de recherche HelloWork.
        Exemple : /emploi/recherche/?k=alternance&l=France&p=2
        """
        q = self.query.replace(" ", "+")
        loc = self.location.replace(" ", "+")
        url = f"{BASE_URL}/emploi/recherche/?k={q}&l={loc}&sort=date"
        if page_num > 1:
            url += f"&p={page_num}"
        return url

    async def _warmup(self, page) -> None:
        print("[hellowork] Warm-up sur hellowork.com...")
        try:
            await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=TIMEOUT_GOTO)
            await asyncio.sleep(random.uniform(1.5, 3.0))
            await human_scroll(page, steps=2)
        except PlaywrightTimeout:
            print("  [warn] Warm-up timeout – on continue quand même")

    async def _load_page_with_retry(self, page, url: str, page_num: int) -> bool:
        for attempt in range(1, MAX_RETRY + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_GOTO)
                await page.wait_for_selector(CARD_SELECTOR, timeout=TIMEOUT_SELECTOR)
                if await is_blocked(page):
                    print(f"  [warn] Page bloquée (tentative {attempt}/{MAX_RETRY})")
                    await asyncio.sleep(random.uniform(10, 20))
                    continue
                return True
            except PlaywrightTimeout:
                print(f"  [warn] Timeout page {page_num} (tentative {attempt}/{MAX_RETRY})")
                if attempt < MAX_RETRY:
                    wait = random.uniform(8, 15)
                    print(f"  → attente {wait:.1f}s avant retry...")
                    await asyncio.sleep(wait)
        return False

    async def _go_to_next_page(self, page) -> bool:
        try:
            next_btn = await page.query_selector(NEXT_PAGE_SELECTOR)
            if not next_btn:
                print("  [info] Pas de bouton Page suivante — dernière page atteinte")
                return False
            await next_btn.scroll_into_view_if_needed()
            await asyncio.sleep(random.uniform(0.5, 1.2))
            await next_btn.click()
            await page.wait_for_selector(CARD_SELECTOR, timeout=TIMEOUT_SELECTOR)
            return True
        except PlaywrightTimeout:
            print("  [warn] Timeout après clic Page suivante")
            return False
        except Exception as e:
            print(f"  [warn] Erreur navigation Page suivante : {e}")
            return False

    async def run(self) -> list[JobOffer]:
        start = datetime.now()
        self.stats["started_at"] = start.isoformat()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=HEADLESS,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale="fr-FR",
                viewport={
                    "width":  random.randint(1200, 1400),
                    "height": random.randint(750,  900),
                },
                extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
            )
            page = await context.new_page()
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            await self._warmup(page)

            first_url = self._build_search_url(page_num=1)
            print(f"\n[hellowork] Page 1/{self.max_pages} → {first_url}")

            if not await self._load_page_with_retry(page, first_url, 1):
                print("[hellowork] Impossible de charger la page 1 — abandon")
                await browser.close()
                return self.offers

            await human_scroll(page)
            page_offers = await extract_offers_from_page(page)
            added = self._add_offers(page_offers)
            print(f"  → {len(page_offers)} offres ({added} nouvelles, {len(page_offers) - added} doublons)")

            for page_num in range(2, self.max_pages + 1):
                delay = random.uniform(DELAY_MIN, DELAY_MAX)
                print(f"  → pause {delay:.1f}s...")
                await asyncio.sleep(delay)

                print(f"[hellowork] Page {page_num}/{self.max_pages} → clic Page suivante")
                if not await self._go_to_next_page(page):
                    # Fallback : navigation directe par URL si le clic échoue
                    fallback_url = self._build_search_url(page_num=page_num)
                    print(f"  [info] Fallback URL → {fallback_url}")
                    if not await self._load_page_with_retry(page, fallback_url, page_num):
                        break

                if await is_blocked(page):
                    print("  [warn] Page bloquée après navigation — arrêt")
                    self.stats["pages_blocked"] += 1
                    break

                await human_scroll(page)
                page_offers = await extract_offers_from_page(page)
                added = self._add_offers(page_offers)
                print(f"  → {len(page_offers)} offres ({added} nouvelles, {len(page_offers) - added} doublons)")

            await browser.close()

        end = datetime.now()
        self.stats["ended_at"]         = end.isoformat()
        self.stats["duration_seconds"] = round((end - start).total_seconds(), 2)
        self.stats["offers_total"]     = len(self.offers)

        print(f"\n[hellowork] Terminé : {len(self.offers)} offres en {self.stats['duration_seconds']}s")
        return self.offers
