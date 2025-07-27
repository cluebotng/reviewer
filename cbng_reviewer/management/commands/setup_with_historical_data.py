import json
import logging
from pathlib import PosixPath
from typing import Any, Optional

from django.conf import settings
from django.core.management import BaseCommand, CommandParser
from social_django.models import UserSocialAuth

from cbng_reviewer.libs.edit_set import EditSetParser
from cbng_reviewer.libs.wikipedia import Wikipedia
from cbng_reviewer.models import User, EditGroup, Edit

logger = logging.getLogger(__name__)
KNOWN_EDIT_SETS = {
    "Original Training Set - C - Train": "C/train.xml",
    "Original Training Set - C - Trail": "C/trial.xml",
    "Original Training Set - D - Train": "D/train.xml",
    "Original Training Set - D - Trail": "D/trial.xml",
    "Original Training Set - D - Bays Train": "D/bayestrain.xml",
    "Original Training Set - D - All": "D/all.xml",
    "Original Testing Training Set - Auto - Train": "Auto/train.xml",
    "Original Testing Training Set - Auto - Trail": "Auto/trial.xml",
    "Original Testing Training Set - Old Triplet - Train": "OldTriplet/train.xml",
    "Original Testing Training Set - Old Triplet - Trail": "OldTriplet/trial.xml",
    "Original Testing Training Set - Old Triplet - Bays Train": "OldTriplet/bayestrain.xml",
    "Original Testing Training Set - Old Triplet - All": "OldTriplet/all.xml",
    "Original Testing Training Set - Random Edits 50/50 - Train": "RandomEdits50-50/train.xml",
    "Original Testing Training Set - Random Edits 50/50 - Trail": "RandomEdits50-50/trial.xml",
    "Original Testing Training Set - Random Edits 50/50 - All": "RandomEdits50-50/all.xml",
    "Original Testing Training Set - Very Large - Train": "VeryLarge/train.xml",
    "Original Testing Training Set - Very Large - Trail": "VeryLarge/trial.xml",
    "Original Testing Training Set - Very Large - Bays Train": "VeryLarge/bayestrain.xml",
    "Original Testing Training Set - Very Large - All": "VeryLarge/all.xml",
}


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--editset-dir")
        parser.add_argument("--editset-name")
        parser.add_argument("--editset-partial-run", action="store_true", default=False)

    def _load_file(self, path: str) -> Any:
        with (settings.BASE_DIR / "data" / path).open("r") as fh:
            return json.loads(fh.read())

    def _ensure_existing_user_accounts_exist(self):
        wikipedia = Wikipedia()
        logger.info("Ensuring user accounts")
        for username in self._load_file("user_accounts.json"):
            if not User.objects.filter(username=username).exists():
                user = User.objects.create(username=username)

                # If the user has a central uid map it to our internal user,
                # so when they authenticate with OAuth things just work
                if central_uid := wikipedia.fetch_user_central_id(username):
                    UserSocialAuth.objects.create(provider="mediawiki", uid=central_uid, user_id=user.id)
                else:
                    logger.warning(f"Not creating mapping for {username} due to no central auth id")

    def _ensure_existing_access_exists(self):
        logger.info("Ensuring user access")
        admin_users = self._load_file("admin_users.json")
        reviewers = self._load_file("approved_reviewers.json")
        for user in User.objects.all():
            user.is_admin = user.username in admin_users
            user.is_reviewer = user.username in reviewers
            user.save()

    def _ensure_existing_edit_groups_exists(self):
        logger.info("Ensuring edit groups")
        for name, weight in self._load_file("edit_groups.json").items():
            edit_group, _ = EditGroup.objects.get_or_create(name=name)
            edit_group.weight = weight
            edit_group.save()

    def _ensure_historical_statistics(self):
        logger.info("Ensuring historical statistics")
        for username, edit_count in self._load_file("historical_edit_counts.json").items():
            user = User.objects.get(username=username)
            user.historical_edit_count = edit_count
            user.save()

    def _ensure_historical_report_data(self):
        logger.info("Ensuring legacy reports")
        target_group = EditGroup.objects.get(name="Legacy Report Interface Import")
        for edit_id, classification in self._load_file("historical_edit_classification.json").items():
            edit, _ = Edit.objects.get_or_create(id=edit_id)
            edit.classification = classification
            edit.status = 2
            edit.groups.add(target_group)
            edit.save()

    def _ensure_edit_set_data(
        self, local_path: Optional[str] = None, name: Optional[str] = None, partial_run: bool = False
    ):
        # These come from the 'edit set' files
        edit_set = EditSetParser()
        for group_name, path in KNOWN_EDIT_SETS.items():
            if name and group_name != name:
                continue

            logger.info(f"Ensuring editset {path}")
            target_group = EditGroup.objects.get(name=group_name)

            if local_path:
                source_file = PosixPath(local_path) / path
                if source_file.exists():
                    edit_set.import_to_group(target_group, source_file, partial_run)
            else:
                edit_set.download_and_import_to_group(target_group, path, partial_run)

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["editset_name"]:
            self._ensure_existing_user_accounts_exist()
            self._ensure_existing_access_exists()
            self._ensure_existing_edit_groups_exists()
            self._ensure_historical_statistics()
            self._ensure_historical_report_data()
        self._ensure_edit_set_data(options["editset_dir"], options["editset_name"], options["editset_partial_run"])
