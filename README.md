# Groupax – Scrappeur intelligent d'offres d'alternance

Plateforme de collecte, analyse et recommandation d'offres d'alternance issues de plusieurs sources en ligne.

## Architecture

```
.
├── scrapers/       # Collecte des offres (Indeed, HelloWork, APEC…)
├── pipeline/       # Nettoyage, déduplication
├── nlp/            # Extraction de compétences, classification, scoring
├── api/            # Backend REST
├── frontend/       # Interface web
└── data/           # Données locales (ignorées par git)
```

## Stack technique

| Couche | Technologie |
|--------|-------------|
| Scraping | Python, Playwright |
| Traitement | Pandas |
| NLP | spaCy / transformers |
| API | FastAPI |
| Frontend | À définir |

## Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

## Lancer le scraper Indeed

```bash
python scrapers/indeed.py
```

Les résultats sont sauvegardés dans `data/indeed_offers.csv` et `data/indeed_offers.json`.
