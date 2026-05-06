import json
import logging
import sys
from pathlib import Path

from database.db import init_db, insert_offers_bulk

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # 1. Initialize database
        logger.info("Initializing database...")
        init_db()

        # 2. Load JSON file from scraper
        json_path = Path("data/indeed_offers.json")
        if not json_path.exists():
            logger.error(f"File not found: {json_path}")
            sys.exit(1)

        with open(json_path, "r", encoding="utf-8") as f:
            offers = json.load(f)

        if not isinstance(offers, list):
            logger.error("JSON file must contain a list of offers")
            sys.exit(1)

        logger.info(f"Loaded {len(offers)} offers from {json_path}")

        # 3. Validate offers
        valid_offers = []
        for idx, offer in enumerate(offers):
            if not isinstance(offer, dict):
                logger.warning(f"Skipping invalid offer at index {idx}: not a dict")
                continue
            if not offer.get("url"):
                logger.warning(f"Skipping offer without URL: {offer.get('title', 'Unknown')}")
                continue
            valid_offers.append(offer)

        logger.info(f"Validated {len(valid_offers)}/{len(offers)} offers")

        # 4. Insert into database
        logger.info(f"Inserting {len(valid_offers)} offers into database...")
        inserted_count = insert_offers_bulk(valid_offers)
        
        logger.info(f"Success! {inserted_count} new offers added to database")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()