"""
Scraper Indeed France – offres d'alternance
Utilise Playwright pour contourner le rendu dynamique.
"""

import asyncio
import csv
import json
import random
import re
import time
from dataclasses import dataclass, asdict, fields
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


# ---------------------------------------------------------------------------
# Modèle de données commun (sera réutilisé par les autres scrapers)
# ---------------------------------------------------------------------------

@dataclass
class JobOffer:
    title: str
    company: str
    location: str
    contract_type: str
    salary: str
    description: str
    url: str
    source: str
    scraped_at: str


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://fr.indeed.com/jobs"
QUERY = "alternance"
MAX_PAGES = 5          # ~75 offres (15 par page)
DELAY_MIN = 2.0        # secondes entre les requêtes
DELAY_MAX = 4.5
OUTPUT_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_delay():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Scraper principal
# ---------------------------------------------------------------------------

class IndeedScraper:

    def __init__(self, query: str = QUERY, location: str = "France", max_pages: int = MAX_PAGES):
        self.query = query
        self.location = location
        self.max_pages = max_pages
        self.offers: list[JobOffer] = []

    def _build_url(self, page: int = 0) -> str:
        start = page * 15
        return (
            f"{BASE_URL}"
            f"?q={self.query.replace(' ', '+')}"
            f"&l={self.location.replace(' ', '+')}"
            f"&sort=date"
            f"&start={start}"
        )

    async def _extract_offers_from_page(self, page) -> list[JobOffer]:
        offers = []

        # Indeed charge les offres dans des cards avec data-jk (job key)
        cards = await page.query_selector_all("div.job_seen_beacon")
        if not cards:
            # Fallback sur un autre sélecteur selon la version d'Indeed
            cards = await page.query_selector_all("li.css-5lfssm")

        for card in cards:
            try:
                title_el   = await card.query_selector("h2.jobTitle span[title]")
                company_el = await card.query_selector("span[data-testid='company-name']")
                location_el = await card.query_selector("div[data-testid='text-location']")
                salary_el  = await card.query_selector("div[data-testid='attribute_snippet_testid']")
                desc_el    = await card.query_selector("div.job-snippet")
                link_el    = await card.query_selector("a[data-jk]")

                title    = clean_text(await title_el.get_attribute("title") if title_el else "")
                company  = clean_text(await company_el.inner_text() if company_el else "")
                location = clean_text(await location_el.inner_text() if location_el else "")
                salary   = clean_text(await salary_el.inner_text() if salary_el else "")
                desc     = clean_text(await desc_el.inner_text() if desc_el else "")

                job_key = await link_el.get_attribute("data-jk") if link_el else ""
                url = f"https://fr.indeed.com/viewjob?jk={job_key}" if job_key else ""

                # Filtrer les offres sans titre (cards publicitaires)
                if not title:
                    continue

                offers.append(JobOffer(
                    title=title,
                    company=company,
                    location=location,
                    contract_type="Alternance",
                    salary=salary,
                    description=desc,
                    url=url,
                    source="indeed",
                    scraped_at=datetime.now().isoformat(),
                ))

            except Exception as e:
                print(f"  [warn] Erreur sur une card : {e}")
                continue

        return offers

    async def run(self) -> list[JobOffer]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="fr-FR",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()

            for page_num in range(self.max_pages):
                url = self._build_url(page_num)
                print(f"[indeed] Page {page_num + 1}/{self.max_pages} → {url}")

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                    # Attendre que les cards soient chargées
                    await page.wait_for_selector("div.job_seen_beacon, li.css-5lfssm", timeout=15_000)
                except PlaywrightTimeout:
                    print(f"  [warn] Timeout page {page_num + 1}, on continue...")
                    continue

                page_offers = await self._extract_offers_from_page(page)
                print(f"  → {len(page_offers)} offres trouvées")
                self.offers.extend(page_offers)

                # Pause entre les pages
                if page_num < self.max_pages - 1:
                    await asyncio.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            await browser.close()

        print(f"\n[indeed] Total : {len(self.offers)} offres collectées")
        return self.offers

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def save_csv(self, filename: str = "indeed_offers.csv") -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / filename
        fieldnames = [f.name for f in fields(JobOffer)]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(asdict(o) for o in self.offers)

        print(f"[indeed] Sauvegardé → {path}")
        return path

    def save_json(self, filename: str = "indeed_offers.json") -> Path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR / filename

        with open(path, "w", encoding="utf-8") as f:
            json.dump([asdict(o) for o in self.offers], f, ensure_ascii=False, indent=2)

        print(f"[indeed] Sauvegardé → {path}")
        return path


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

async def main():
    scraper = IndeedScraper(query="alternance", location="France", max_pages=5)
    await scraper.run()
    scraper.save_csv()
    scraper.save_json()


if __name__ == "__main__":
    asyncio.run(main())
