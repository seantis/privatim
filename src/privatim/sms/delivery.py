import argparse
import configparser
import errno
import json
import os
import requests
import stat
import time
from operator import itemgetter
from pyramid.paster import setup_logging

from .logger import logger


from typing import cast
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.types import JSONObject


MAX_SEND_TIME = 60 * 60 * 3


class QueuedSMSDelivery:

    path: str
    username: str
    password: str

    def __init__(self, path: str, username: str, password: str):
        self.path = path
        self.username = username
        self.password = password

    def _send(
            self,
            recipients: list[str],
            content: str,
            sender: str = 'Privatim'
    ) -> None:

        response = requests.post(  # nosec:B113
            'https://json.aspsms.com/SendSimpleTextSMS',
            json={
                'UserName': self.username,
                'Password': self.password,
                'Originator': sender,
                'Recipients': recipients,
                'MessageText': content
            }
        )

        response.raise_for_status()
        result = response.json()
        if result.get('StatusInfo') != 'OK' or result.get('StatusCode') != '1':
            raise Exception(f'Sending SMS failed, got: "{str(result)}"')

    def _parseMessage(self, filename: str) -> 'JSONObject':
        with open(filename, 'r') as fd:
            data = json.load(fd)

        assert isinstance(data, dict)
        return data

    def send_messages(self) -> None:
        # We expect to messages to in E.164 format, eg. '+41780000000'
        messages = [
            (m := os.path.join(self.path, x), os.path.getmtime(m))
            for x in os.listdir(self.path)
            if x.endswith('.json')
        ]

        # Sort by modification time so earlier messages are sent before
        # later messages during queue processing.
        messages.sort(key=itemgetter(1))
        for filename, _timestamp in messages:
            self._send_message(filename)

    def _send_message(self, filename: str) -> None:
        head, tail = os.path.split(filename)
        tmp_filename = os.path.join(head, '.sending-' + tail)
        rejected_filename = os.path.join(head, '.rejected-' + tail)
        try:
            # perform a series of operations in an attempt to ensure
            # that no two threads/processes send this message
            # simultaneously as well as attempting to not generate
            # spurious failure messages in the log; a diagram that
            # represents these operations is included in a
            # comment above this class
            try:
                # find the age of the tmp file (if it exists)
                mtime = os.stat(tmp_filename)[stat.ST_MTIME]
            except OSError as e:
                if e.errno == errno.ENOENT:
                    # file does not exist
                    # the tmp file could not be stated because it
                    # doesn't exist, that's fine, keep going
                    age = None
                else:
                    # the tmp file could not be stated for some reason
                    # other than not existing; we'll report the error
                    raise
            else:
                age = time.time() - mtime

            # if the tmp file exists, check it's age
            if age is not None:
                try:
                    if age > MAX_SEND_TIME:
                        # the tmp file is "too old"; this suggests
                        # that during an attemt to send it, the
                        # process died; remove the tmp file so we
                        # can try again
                        os.remove(tmp_filename)
                    else:
                        # the tmp file is "new", so someone else may
                        # be sending this message, try again later
                        return
                    # if we get here, the file existed, but was too
                    # old, so it was unlinked
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        # file does not exist
                        # it looks like someone else removed the tmp
                        # file, that's fine, we'll try to deliver the
                        # message again later
                        return

            # now we know that the tmp file doesn't exist, we need to
            # "touch" the message before we create the tmp file so the
            # mtime will reflect the fact that the file is being
            # processed (there is a race here, but it's OK for two or
            # more processes to touch the file "simultaneously")
            try:
                os.utime(filename, None)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    # file does not exist
                    # someone removed the message before we could
                    # touch it, no need to complain, we'll just keep
                    # going
                    return
                else:
                    # Some other error, propogate it
                    raise

            # creating this hard link will fail if another process is
            # also sending this message
            try:
                os.link(filename, tmp_filename)
            except OSError as e:
                if e.errno == errno.EEXIST:
                    # file exists, *nix
                    # it looks like someone else is sending this
                    # message too; we'll try again later
                    return
                else:
                    # Some other error, propogate it
                    raise

            # read message file and send contents
            data = self._parseMessage(filename)
            recipients = data.get('Recipients', [])
            content = data.get('MessageText', '')
            sender = data.get('Originator', '')
            if (
                recipients and content and sender and
                # validate the types of payload, so an attacker
                # can't insert arbitrary JSON data within these
                # three keys
                isinstance(recipients, list) and
                all(isinstance(r, str) for r in recipients) and
                isinstance(content, str) and isinstance(sender, str)
            ):
                sanitized_recipients = cast('list[str]', recipients)
                self._send(sanitized_recipients, content, sender)
            else:
                sanitized_recipients = []
                logger.error(
                    'Discarding SMS {} due to invalid content/number'.format(
                        filename
                    )
                )
                os.link(filename, rejected_filename)

            try:
                os.remove(filename)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    # file does not exist
                    # someone else unlinked the file; oh well
                    pass
                else:
                    # something bad happend, log it
                    raise

            try:
                os.remove(tmp_filename)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    # file does not exist
                    # someone else unlinked the file; oh well
                    pass
                else:
                    # something bad happened, log it
                    raise

            logger.info(f'SMS to {", ".join(sanitized_recipients)} sent.')

        # Catch errors and log them here
        except Exception:
            logger.error(f'Error while sending SMS {filename}', exc_info=True)


def main() -> None:

    parser = argparse.ArgumentParser(description='Delivers queued sms')
    parser.add_argument('--config', help='Config file')
    parser.add_argument('smsdir', help='smsdir')
    args = parser.parse_args()

    setup_logging(args.config)

    settings = {'username': '', 'password': ''}
    config = configparser.SafeConfigParser()
    config.read(args.config)
    for section_name in config.sections():
        if config.has_option(section_name, 'username'):
            settings.update(dict(config.items(section_name)))

    if os.path.exists(args.smsdir):
        delivery = QueuedSMSDelivery(
            args.smsdir,
            settings['username'],
            settings['password'],
        )
        delivery.send_messages()
