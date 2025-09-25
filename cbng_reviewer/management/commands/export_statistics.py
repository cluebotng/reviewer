import logging
from typing import Any

from cbng_reviewer.libs.stats import Statistics
from cbng_reviewer.libs.wikipedia.management import WikipediaManagement
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)


class Command(CommandWithMetrics):
    def handle(self, *args: Any, **options: Any) -> None:
        """Export stats to wikipedia."""
        statistics = Statistics()

        wikipedia_management = WikipediaManagement()
        if wiki_markup := statistics.generate_wikimarkup():
            wikipedia_management.update_statistics_page(wiki_markup)
        else:
            logger.warning("No wiki markup generated - not updating page")
