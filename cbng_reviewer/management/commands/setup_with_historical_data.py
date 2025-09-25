import functools
import json
import logging
import tempfile
from pathlib import PosixPath
from typing import Any, Optional

from django.conf import settings
from django.core.management import CommandParser
from social_django.models import UserSocialAuth

from cbng_reviewer.libs.edit_set.parser import EditSetParser
from cbng_reviewer.libs.edit_set.utils import import_wp_edit_to_edit_group
from cbng_reviewer.libs.utils import download_file
from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User, EditGroup, Edit
from cbng_reviewer.utils.command import CommandWithMetrics

logger = logging.getLogger(__name__)
KNOWN_EDIT_SETS = {
    ("Original Training Set - C", "Train"): "C/train.xml",
    ("Original Training Set - C", "Trail"): "C/trial.xml",
    ("Original Training Set - D", "Train"): "D/train.xml",
    ("Original Training Set - D", "Trail"): "D/trial.xml",
    ("Original Training Set - D", "Bayes Train"): "D/bayestrain.xml",
    ("Original Training Set - D", "All"): "D/all.xml",
    ("Original Testing Training Set - Auto", "Train"): "Auto/train.xml",
    ("Original Testing Training Set - Auto", "Trail"): "Auto/trial.xml",
    ("Original Testing Training Set - Old Triplet", "Train"): "OldTriplet/train.xml",
    ("Original Testing Training Set - Old Triplet", "Trail"): "OldTriplet/trial.xml",
    ("Original Testing Training Set - Old Triplet", "Bays Train"): "OldTriplet/bayestrain.xml",
    ("Original Testing Training Set - Old Triplet", "All"): "OldTriplet/all.xml",
    ("Original Testing Training Set - Random Edits 50/50", "Train"): "RandomEdits50-50/train.xml",
    ("Original Testing Training Set - Random Edits 50/50", "Trail"): "RandomEdits50-50/trial.xml",
    ("Original Testing Training Set - Random Edits 50/50", "All"): "RandomEdits50-50/all.xml",
    ("Original Testing Training Set - Very Large", "Train"): "VeryLarge/train.xml",
    ("Original Testing Training Set - Very Large", "Trail"): "VeryLarge/trial.xml",
    ("Original Testing Training Set - Very Large", "Bays Train"): "VeryLarge/bayestrain.xml",
    ("Original Testing Training Set - Very Large", "All"): "VeryLarge/all.xml",
}


class Command(CommandWithMetrics):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--editset-dir")
        parser.add_argument("--editset-name")
        parser.add_argument("--editset-skip-existing", action="store_true", default=False)

        parser.add_argument("--editdb-dir")
        parser.add_argument("--editdb-name")
        parser.add_argument("--editdb-skip-existing", action="store_true", default=False)

    def _load_file(self, path: str) -> Any:
        with (settings.BASE_DIR / "data" / path).open("r") as fh:
            return json.loads(fh.read())

    def _ensure_existing_user_accounts_exist(self):
        wikipedia_reader = WikipediaReader()
        logger.info("Ensuring user accounts")
        for username in self._load_file("user_accounts.json"):
            if not User.objects.filter(username=username).exists():
                user = User.objects.create(username=username)

                # If the user has a central uid map it to our internal user,
                # so when they authenticate with OAuth things just work
                central_uid, _ = wikipedia_reader.get_user(username)
                if central_uid:
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
        self, local_path: Optional[str] = None, name: Optional[str] = None, skip_existing: bool = False
    ):
        # These come from the 'edit set' files
        editset_parser = EditSetParser()
        for (parent_group_name, group_name), path in KNOWN_EDIT_SETS.items():
            if name and f"{parent_group_name} - {group_name}" != name:
                continue

            logger.info(f"Ensuring editset {path}")
            target_parent_group, _ = EditGroup.objects.get_or_create(name=parent_group_name)
            target_group, _ = EditGroup.objects.get_or_create(name=group_name, related_to=target_parent_group)

            callback_func = functools.partial(
                import_wp_edit_to_edit_group,
                target_group=target_group,
                skip_existing=skip_existing,
                force_status=True,
            )

            if local_path:
                source_file = PosixPath(local_path) / path
                if source_file.exists():
                    editset_parser.read_file(source_file, callback_func)
            else:
                with tempfile.NamedTemporaryFile() as file:
                    source_url = f"https://cluebotng-editsets.toolforge.org/editdb/{path}"
                    target_file = PosixPath(file)
                    logger.info(f"Downloading {source_url} to {target_file.as_posix()}")
                    download_file(target_file, source_url)
                    editset_parser.read_file(target_file, callback_func)

    def _ensure_edit_db_data(
        self, local_path: Optional[str] = None, name: Optional[str] = None, skip_existing: bool = False
    ):
        logger.info(f"Ensuring editdb entries from {name}")
        target_parent_group, _ = EditGroup.objects.get_or_create(name="Edit DB")
        editset_parser = EditSetParser()

        callback_func = functools.partial(
            import_wp_edit_to_edit_group,
            target_group=target_parent_group,
            skip_existing=skip_existing,
            dynamic_group_from_source=True,
            force_status=True,
        )

        if local_path:
            source_file = PosixPath(local_path) / name
            if source_file.exists():
                editset_parser.read_file(source_file, callback_func)
        else:
            with tempfile.NamedTemporaryFile() as file:
                source_url = f"https://cluebotng-editsets.toolforge.org/editdb/{name}"
                target_file = PosixPath(file.name)
                logger.info(f"Downloading {source_url} to {target_file.as_posix()}")
                download_file(target_file, source_url)
                editset_parser.read_file(target_file, callback_func)

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["editset_name"] and not options["editdb_name"]:
            self._ensure_existing_user_accounts_exist()
            self._ensure_existing_access_exists()
            self._ensure_existing_edit_groups_exists()
            self._ensure_historical_statistics()
            self._ensure_historical_report_data()

        if options["editset_name"]:
            self._ensure_edit_set_data(
                options["editset_dir"], options["editset_name"], options["editset_skip_existing"]
            )

        if options["editdb_name"]:
            self._ensure_edit_db_data(options["editdb_dir"], options["editdb_name"], options["editdb_skip_existing"])
