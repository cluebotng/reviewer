from typing import Any

from django.conf import settings
from django.core.management import BaseCommand

from cbng_reviewer.libs.stats import Statistics
from cbng_reviewer.libs.wikipedia import Wikipedia


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Export stats to wikipedia."""
        statistics = Statistics()

        wikipedia = Wikipedia()
        markup = wikipedia.generate_statistics_wikimarkup(
            statistics.get_edit_group_statistics(),
            statistics.get_user_statistics(True),
        )

        if settings.WIKIPEDIA_USERNAME and settings.WIKIPEDIA_PASSWORD:
            wikipedia.login(settings.WIKIPEDIA_USERNAME, settings.WIKIPEDIA_PASSWORD)
        wikipedia.update_statistics_page(markup)
