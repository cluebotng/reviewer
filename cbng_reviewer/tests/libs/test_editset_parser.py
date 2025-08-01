from datetime import datetime
from pathlib import PosixPath
from tempfile import NamedTemporaryFile
from typing import List

from django.conf import settings
from django.test import TestCase

from cbng_reviewer.libs.edit_set.parser import EditSetParser
from cbng_reviewer.libs.models.edit_set import WpEdit


class CallbackHandler:
    wp_edits: List[WpEdit]

    def __init__(self):
        self.wp_edits = []

    def callback_func(self, wp_edit: WpEdit):
        self.wp_edits.append(wp_edit)


class EditSetParserTestCase(TestCase):
    def testMissingFile(self):
        callback = CallbackHandler()
        parser = EditSetParser()
        with NamedTemporaryFile() as file:
            parser.read_file(PosixPath(file.name), callback.callback_func)
        self.assertEqual(callback.wp_edits, [])

    def testEmptyFile(self):
        callback = CallbackHandler()
        parser = EditSetParser()
        with NamedTemporaryFile() as file:
            with open(file.name, "w") as fh:
                fh.write("")
            parser.read_file(PosixPath(file.name), callback.callback_func)
        self.assertEqual(callback.wp_edits, [])

    def testBadFile(self):
        callback = CallbackHandler()
        parser = EditSetParser()
        parser.read_file(
            settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "editsets" / "bad.xml", callback.callback_func
        )
        self.assertEqual(callback.wp_edits, [])

    def testSingleEdit(self):
        callback = CallbackHandler()
        parser = EditSetParser()
        parser.read_file(
            settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "editsets" / "single.xml", callback.callback_func
        )
        self.assertEqual(len(callback.wp_edits), 1)

        edit = callback.wp_edits[0]
        self.assertEqual(edit.edit_id, 1234)
        self.assertEqual(edit.title, "Experiment")
        self.assertEqual(edit.namespace, "main")
        self.assertEqual(edit.comment, "Hello World")
        self.assertEqual(edit.user, "Bob Smith")
        self.assertEqual(edit.creator, "Jane Smith")
        self.assertEqual(edit.page_made_time, datetime(1970, 1, 1, 0, 20, 20))
        self.assertEqual(edit.user_edit_count, 5)
        self.assertEqual(edit.user_distinct_pages, 6)
        self.assertEqual(edit.user_warns, 2)
        self.assertEqual(edit.user_reg_time, datetime(1970, 1, 1, 15, 5, 21))
        self.assertEqual(edit.prev_user, "Jill Smith")
        self.assertEqual(edit.num_recent_edits, 1)
        self.assertEqual(edit.num_recent_reversions, 3)
        self.assertEqual(edit.is_vandalism, False)

        self.assertEqual(edit.current.minor, True)
        self.assertEqual(edit.current.text, "current")
        self.assertEqual(edit.current.timestamp, datetime(1970, 1, 1, 0, 20, 34))

        self.assertEqual(edit.previous.minor, False)
        self.assertEqual(edit.previous.text, "previous")
        self.assertEqual(edit.previous.timestamp, datetime(1970, 1, 1, 0, 20, 30))

    def testMultipleEdits(self):
        callback = CallbackHandler()
        parser = EditSetParser()
        parser.read_file(
            settings.BASE_DIR / "cbng_reviewer" / "tests" / "data" / "editsets" / "multiple.xml", callback.callback_func
        )
        self.assertEqual(len(callback.wp_edits), 3)

        self.assertEqual(callback.wp_edits[0].title, "Christchurch and Lymington (UK Parliament constituency)")
        self.assertEqual(callback.wp_edits[1].title, "Head")
        self.assertEqual(callback.wp_edits[2].title, "Nelson Cuevas")
