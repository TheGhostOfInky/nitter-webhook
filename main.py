import os, sched, datetime, logging
from random import randint
from itertools import islice
from typing import Generator, Iterable, TypeVar
from nitter_wrapper import TweetStream
from discord_webhook import Webhook
from sqlite3_dbdriver import DB
try:
    import tomllib
except ImportError:
    import tomli as tomllib

T = TypeVar("T")


def batched(iterable: Iterable[T], n: int) -> Generator[list[T], None, None]:
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch


DIR_NAME = os.path.dirname(os.path.realpath(__file__))

with open(DIR_NAME + "/config.toml", "rb") as f:
    config = tomllib.load(f)

# Global variables defined at startup
db: DB
last_time: datetime.datetime
webhook: Webhook

user_name: str = config["user-name"]
delay: int = config.get("delay", 600)
instance: str = config.get("instance", "https://nitter.net")


def post() -> None:
    global last_time

    tweets = TweetStream(user_name, instance)
    newer = tweets.newer_than(last_time)

    now = datetime.datetime.now(tz=datetime.timezone.utc)

    db.set("last-time", now.isoformat())
    last_time = now

    if newer:
        for tw in batched(newer, 10):
            webhook.post_to_webhook(tw)

        logging.info(f"Posted {len(newer)} tweet(s)")
    else:
        logging.info("No new tweets to post")


def main(scheduler: sched.scheduler) -> None:
    scheduler.enter(delay, 1, main, (scheduler,))

    try:
        post()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    logging.basicConfig(
        filename="nitter-webhook.log",
        filemode="a",
        format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
        level=logging.INFO
    )

    db = DB(DIR_NAME + "/time.db")

    if lt := db.get("last-time"):
        last_time = datetime.datetime.fromisoformat(lt)
        logging.info(f"Loaded {lt} from database")
    else:
        last_time = datetime.datetime.now(tz=datetime.timezone.utc)
        logging.info("No previous time found in database, defaulting to current time")

    webhook = Webhook(
        config["webhook-url"], user_name,
        config.get("pfp", ""),
        config.get("ping-roles", []),
        instance
    )

    scheduler = sched.scheduler()
    scheduler.enter(2, 1, main, (scheduler, ))

    try:
        scheduler.run()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Got signal to exit")

        for x in scheduler.queue:
            scheduler.cancel(x)

    del db
    exit(0)
