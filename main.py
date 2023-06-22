import os, sched, datetime, logging
from random import randint
from itertools import islice
from typing import Generator, Iterable, TypeVar
from twitter_wrapper import TweetStream
from discord_webhook import Webhook
from sqlite3_dbdriver import DB
try:
    import tomllib
except ImportError:
    import tomli as tomllib

T = TypeVar("T")


def batched(iterable: Iterable[T], n: int) -> Generator[tuple[T, ...], None, None]:
    it = iter(iterable)
    while (batch := tuple(islice(it, n))):
        yield batch


DIR_NAME = os.path.dirname(os.path.realpath(__file__))

with open(DIR_NAME + "/config.toml", "rb") as f:
    config = tomllib.load(f)

db = DB(DIR_NAME + "/time.db")

last_time: datetime.datetime

if lt := db.get("last-time"):
    last_time = datetime.datetime.fromisoformat(lt)
else:
    last_time = datetime.datetime.now(tz=datetime.timezone.utc)

user_name = config["user-name"]
limit: int = config.get("limit", 20)
delay: int = config.get("delay", 550)
rand_range: int = config.get("rand-range", 100)

webhook = Webhook(
    config["webhook-url"], user_name,
    config.get("pfp", ""),
    config.get("ping-roles", [])
)


def post() -> None:
    global last_time

    tweets = TweetStream(user_name=user_name, count=limit)
    newer = tweets.newer_than(last_time)

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    last_time = now
    db.set("last-time", now.isoformat())

    if newer:
        for tw in batched(newer, 10):
            webhook.post_to_webhook(list(tw))

        logging.info(f"Posted {len(newer)} tweets")
    else:
        logging.info("No new tweets to post")


def main(scheduler: sched.scheduler) -> None:

    l_delay = delay + randint(0, rand_range)
    scheduler.enter(l_delay, 1, main, (scheduler,))

    try:
        post()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    logging.basicConfig(
        filename="twitter-webhook.log",
        filemode="a",
        format="%(asctime)s:%(levelname)s:%(name)s: %(message)s",
        level=logging.INFO
    )

    scheduler = sched.scheduler()
    scheduler.enter(2, 1, main, (scheduler, ))

    try:
        scheduler.run()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Got signal to exit")
        for x in scheduler.queue:
            scheduler.cancel(x)
