"""
pipeline/deduplicator.py
========================
Déduplication des offres avant insertion en base.

Deux niveaux de déduplication :
1. Par URL (rapide, exact) — géré directement par SQLite via INSERT OR IGNORE
2. Par empreinte contenu (title + company + location) — pour les offres sans URL
   ou publiées sur plusieurs sites avec des URLs différentes
"""

import hashlib
import logging
from dataclasses import asdict

from database.db import insert_offers_bulk, url_exists

logger = logging.getLogger(__name__)


# =============================================================================
# SECTION 1 – EMPREINTE DE CONTENU
# =============================================================================

def content_fingerprint(offer: dict) -> str:
    """
    Calcule une empreinte unique basée sur le contenu de l'offre.

    Utilisée pour détecter les doublons inter-sources :
    la même offre publiée sur Indeed et HelloWork aura la même empreinte.

    On normalise les champs avant de hasher pour ignorer
    les différences de casse, espaces, accents, etc.

    Args:
        offer : Dictionnaire représentant une offre

    Returns:
        Hash MD5 hexadécimal (32 caractères)
    """
    key = "|".join([
        offer.get("title", "").lower().strip(),
        offer.get("company", "").lower().strip(),
        offer.get("location", "").lower().strip(),
    ])
    return hashlib.md5(key.encode()).hexdigest()


# =============================================================================
# SECTION 2 – FILTRE DE DÉDUPLICATION
# =============================================================================

def deduplicate(offers: list[dict]) -> list[dict]:
    """
    Filtre une liste d'offres pour ne garder que les nouvelles.

    Étapes :
    1. Déduplication interne au batch (même URL ou même empreinte contenu)
    2. Déduplication contre la base (vérifie si l'URL existe déjà)

    Args:
        offers : Liste d'offres fraîchement scrapées

    Returns:
        Sous-liste contenant uniquement les offres inédites
    """
    seen_urls         = set()
    seen_fingerprints = set()
    unique: list[dict] = []
    duplicates_count = 0

    for offer in offers:
        url         = offer.get("url", "")
        fingerprint = content_fingerprint(offer)

        # --- Dédup interne au batch ---
        if url and url in seen_urls:
            logger.debug(f"Duplicate URL in batch: {url}")
            duplicates_count += 1
            continue
        if fingerprint in seen_fingerprints:
            logger.debug(f"Duplicate fingerprint: {offer.get('title')}")
            duplicates_count += 1
            continue

        # --- Dédup contre la base (par URL) ---
        if url and url_exists(url):
            logger.debug(f"Offer already exists in database: {url}")
            duplicates_count += 1
            continue

        seen_urls.add(url)
        seen_fingerprints.add(fingerprint)
        unique.append(offer)

    logger.info(f"Deduplication: {len(offers)} offers → {len(unique)} unique (skipped {duplicates_count})")
    return unique


# =============================================================================
# SECTION 3 – POINT D'ENTRÉE PIPELINE
# =============================================================================

def process_and_save(offers) -> int:
    """
    Pipeline complet : déduplication → insertion en base.

    Accepte aussi bien une liste de JobOffer (dataclass) que
    des dictionnaires bruts.

    Args:
        offers : Liste de JobOffer ou de dict

    Returns:
        Nombre d'offres réellement insérées
    """
    try:
        if not offers:
            logger.warning("process_and_save called with empty list")
            return 0
        
        logger.info(f"Processing {len(offers)} offers...")
        
        # Conversion dataclass → dict si nécessaire
        offer_dicts = []
        for o in offers:
            try:
                offer_dicts.append(asdict(o) if hasattr(o, "__dataclass_fields__") else o)
            except Exception as e:
                logger.warning(f"Failed to convert offer to dict: {e}")
                continue

        unique = deduplicate(offer_dicts)
        
        if not unique:
            logger.info("No unique offers to insert")
            return 0
        
        inserted = insert_offers_bulk(unique)
        logger.info(f"Pipeline result: {len(offers)} → {len(unique)} unique → {inserted} inserted")
        return inserted
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        raise
