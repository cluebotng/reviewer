import logging
from typing import Any

from django.conf import settings
from django.core.management import BaseCommand

from cbng_reviewer.libs.stats import Statistics
from cbng_reviewer.libs.wikipedia import Wikipedia

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Export stats to wikipedia."""
        statistics = Statistics()

        wikipedia = Wikipedia(True)
        if wiki_markup := statistics.generate_wikimarkup():
            wikipedia.update_statistics_page(wiki_markup)
        else:
            logger.warning("No wiki markup generated - not updating page")
