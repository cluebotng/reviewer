import logging
from typing import Any

from django.core.management import BaseCommand

from cbng_reviewer.libs.report_interface import ReportInterface
from cbng_reviewer.models import EditGroup, User, Classification

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Add a review if this appears to be a bug driven false positive"""
        report_interface = ReportInterface()
        user = User.objects.get(username="Bot - ClueBot NG")
        our_classified_edits = Classification.objects.filter(user=user).values_list("edit__id", flat=True)
        edit_group = EditGroup.objects.get(name="2025 temp account bug")
        for edit in edit_group.edit_set.filter(pk__in=our_classified_edits):
            report_interface.create_report_for_edit(edit.id)
