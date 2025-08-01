from django.test import TestCase
from django.test.utils import override_settings

from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.models.message import Message


class IrcRelayTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        self.message = Message(body="")
        super(IrcRelayTestCase, self).__init__(*args, **kwargs)

    def testNoMessageOnMissingConfig(self):
        with override_settings(IRC_RELAY_HOST=None, IRC_RELAY_PORT=None, IRC_RELAY_CHANNEL=None):
            self.assertFalse(IrcRelay().send_message(self.message))

    def testNoMessageWhenDisabled(self):
        with override_settings(CBNG_ENABLE_IRC_MESSAGING=False):
            self.assertFalse(IrcRelay().send_message(self.message))

    def testMessage(self):
        with override_settings(
            IRC_RELAY_HOST="localhost",
            IRC_RELAY_PORT=1234,
            IRC_RELAY_CHANNEL="#development",
            CBNG_ENABLE_IRC_MESSAGING=True,
        ):
            self.assertFalse(IrcRelay().send_message(self.message))
