import logging

from django.conf import settings
from django.db.models import Count
from prometheus_client import Gauge

from cbng_reviewer.models import (
    EditGroup,
    Edit,
    STATUSES,
    CLASSIFICATIONS,
)

logger = logging.getLogger(__name__)

# These need to be registered once, so do it on import
edits_by_status_count = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_edits_by_status_count",
    "Number of edits by status",
    ["status"],
)

edit_group_by_status_count = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_edit_group_edits_by_status_count",
    "Number of edits by status in an edit group",
    ["group", "status"],
)

edits_by_classification_count = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_edits_by_classification_count",
    "Number of edits by classification",
    ["classification"],
)

edit_group_by_classification_count = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_edit_group_edits_by_classification_count",
    "Number of edits by classification in an edit group",
    ["group", "classification"],
)

edits_marked_deleted_count = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_edits_marked_deleted_count",
    "Number of edits that are marked as deleted",
)

edits_with_training_data_count = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_edits_with_training_data_count",
    "Number of edits that are marked as having training data",
)


class MetricsExporter:
    def _update_edits_by_status_count(self):
        counts_by_status = {
            row["status"]: row["count"] for row in Edit.objects.values("status").annotate(count=Count("id"))
        }

        for db_id, label in STATUSES:
            edits_by_status_count.labels(status=label).set(counts_by_status.get(db_id, 0))

    def _edit_group_by_status_count(self):
        counts_by_status = {
            (row["groups__id"], row["status"]): row["count"]
            for row in Edit.objects.values("groups__id", "status").annotate(count=Count("id"))
        }

        for edit_group in EditGroup.objects.all():
            for db_id, label in STATUSES:
                edit_group_by_status_count.labels(group=edit_group.contextual_name, status=label).set(
                    counts_by_status.get((edit_group.id, db_id), 0)
                )

    def _update_edits_by_classification_count(self):
        counts_by_classification = {
            row["classification"]: row["count"]
            for row in Edit.objects.values("classification").annotate(count=Count("id"))
        }

        for db_id, label in CLASSIFICATIONS:
            edits_by_classification_count.labels(classification=label).set(counts_by_classification.get(db_id, 0))

    def _edit_group_by_classification_count(self):
        counts_by_classification = {
            (row["groups__id"], row["classification"]): row["count"]
            for row in Edit.objects.values("groups__id", "classification").annotate(count=Count("id"))
        }

        for edit_group in EditGroup.objects.all():
            for db_id, label in CLASSIFICATIONS:
                edit_group_by_classification_count.labels(group=edit_group.contextual_name, classification=label).set(
                    counts_by_classification.get((edit_group.id, db_id), 0)
                )

    def _edit_classification_count(self):
        edits_marked_deleted_count.set(Edit.objects.filter(is_deleted=True).count())
        edits_with_training_data_count.set(Edit.objects.filter(has_training_data=True).count())

    def update_metrics(self):
        self._update_edits_by_status_count()
        self._edit_group_by_status_count()
        self._update_edits_by_classification_count()
        self._edit_group_by_classification_count()
        self._edit_classification_count()
