import logging
from abc import ABC
from datetime import datetime, timezone

import requests
from django.conf import settings
from django.core.management import BaseCommand
from prometheus_client import Gauge, CollectorRegistry, generate_latest

logger = logging.getLogger(__name__)
management_command_registry = CollectorRegistry()

management_command_execute_time = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_management_command_execution_runtime",
    "Runtime for a management command",
    registry=management_command_registry,
)

management_command_last_run_time = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_management_command_last_execution_time",
    "Last execution time for a management command",
    registry=management_command_registry,
)

management_command_successful = Gauge(
    f"{settings.PROMETHEUS_METRIC_NAMESPACE}_management_command_successful",
    "If the run was successful management command",
    registry=management_command_registry,
)


def send_metrics_to_pushgateway(command: str):
    try:
        r = requests.post(
            f"http://pushgateway:9091/metrics/job/{command}",
            data=generate_latest(management_command_registry),
            timeout=2,
        )
    except Exception as e:
        logger.warning(f"Exception occurred while sending metrics to pushgateway: {e}")
    else:
        if r.status_code != 200:
            logger.warning(f"Failed to send metrics to pushgateway: {r.status_code} / {r.text}")


class CommandWithMetrics(BaseCommand, ABC):

    def execute(self, *args, **options):
        command = self.__class__.__module__.split(".")[-1]
        try:
            start_time = datetime.now(tz=timezone.utc)
            super(CommandWithMetrics, self).execute(*args, **options)
            end_time = datetime.now(tz=timezone.utc)

            management_command_execute_time.set((end_time - start_time).total_seconds())
            management_command_last_run_time.set(end_time.timestamp())
            management_command_successful.set(1)
        except Exception as e:
            management_command_successful.set(0)
            raise e
        finally:
            send_metrics_to_pushgateway(command)
