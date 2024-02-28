"""For posting sticky messages to Discord."""

import logging
import typing
import json
import time
import sys

import requests


class Looper():
    """Looping class to continuously check for updates."""

    def __init__(self,
                 filename: str,
                 channels: typing.Dict[str, str],
                 token: str) -> None:
        self.url = "https://discordapp.com/api/channels/{}/messages"
        self.headers = {"Authorization": f"Bot {token}"}
        self.channels = channels
        self.filename = filename
        self.timeout = 60

        try:
            self.message_ids = get_json(filename)
        except FileNotFoundError:
            self.message_ids = {channel: None for channel in channels}

    def run(self) -> None:
        """Main entry point."""

        while True:
            self.loop()

    def loop(self) -> None:
        """Run one cycle."""

        for channel_id in self.message_ids:
            self.try_update(channel_id)

        self.sleep()

    def try_update(self, channel_id: str) -> None:
        """Try to Update a Channel's Sticky Message."""

        try:
            self.update(channel_id)
        except (requests.exceptions.Timeout,
                requests.exceptions.ConnectionError) as exception:
            logging.error(exception)

    def update(self, channel_id: str) -> None:
        """Update a Channel's Sticky Message."""

        if self.valid(channel_id):
            return

        logging.info("Creating Sticky Message for '%s'...", channel_id)

        response = requests.post(
            self.url.format(channel_id),
            {"content": self.channels[channel_id]},
            headers=self.headers,
            timeout=self.timeout
        )

        if self.not_ok(response):
            return

        message_id = response.json()["id"]
        logging.info("Created '%s'.", message_id)
        self.message_ids[channel_id] = message_id
        self.update_json()

    def valid(self, channel_id: str) -> bool:
        """Does this Channel have a valid Sticky Message?"""

        message_id = self.message_ids[channel_id]

        if message_id is None:
            return False

        response = requests.get(
            self.url.format(channel_id),
            {"after": message_id},
            headers=self.headers,
            timeout=self.timeout
        )

        if self.not_ok(response) or not response.json():
            return True

        self.sleep()

        logging.info("Deleting Sticky Message '%s'...", message_id)

        response = requests.delete(
            self.url.format(channel_id) + f"/{message_id}",
            headers=self.headers,
            timeout=self.timeout
        )

        success = response.status_code in [204, 404]

        if success:
            self.message_ids[channel_id] = None
            logging.info("Deleted.")
            self.update_json()
        else:
            logging.error(response.content)

        return not success

    def update_json(self) -> None:
        """Write updated JSON to file."""

        with get_file(self.filename, 'w') as file:
            json.dump(self.message_ids, file)

    def not_ok(self, response: requests.Response) -> bool:
        """Is the Response not OK (200)?"""

        result = response.status_code != 200

        if result:
            logging.error(response.content)

        return result

    def sleep(self) -> None:
        """Sleep for Discord API."""

        time.sleep(2)


def get_json(filename: str) -> typing.Any:
    """Get JSON file contents."""

    with get_file(filename) as file:
        return json.load(file)


def get_file(filename: str, mode: str = 'r') -> typing.IO[any]:
    """Get a file stream."""
    return open(filename, mode, encoding="utf-8")


def main() -> None:
    """Main entry method when running the script directly."""

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    args = sys.argv
    Looper(args[2], **get_json(args[1])).run()


if __name__ == '__main__':
    main()
