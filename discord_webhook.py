from typing import Any
from nitter_wrapper import Tweet
import requests, re

FOOTER = {
    "text": "Via Twitter",
    "icon_url": "https://i.imgur.com/PFGs0WA.png"
}


def clean_urls(inp: str) -> str:
    sub = re.sub(r"https?:\/\/\S+", "", inp)
    return re.sub(r"@(\S+)", r"[@\1](https://twitter.com/\1)", sub)


def create_fields(tweet: Tweet) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    images, urls = tweet.images, tweet.urls

    for i in images[1::]:
        fields.append({
            "name": "Additional image:",
            "value": i
        })

    for i in urls:
        fields.append({
            "name": "Link:",
            "value": i
        })

    return fields


class Webhook:
    url: str
    username: str
    pfp: str
    ping_roles: list[str]

    def __init__(self, url: str, username: str, pfp: str, ping_roles: str | list[str]) -> None:
        self.username = username
        self.url = url
        self.pfp = pfp

        if isinstance(ping_roles, str):
            self.ping_roles = [ping_roles]
        else:
            self.ping_roles = ping_roles

    def create_tweet_embed(self, tweet: Tweet) -> dict:
        embed: dict[str, Any] = {
            "title": f"New tweet by @{self.username}",
            "description": clean_urls(tweet.text),
            "timestamp": tweet.time.isoformat(),
            "color": 0x179cf0,
            "footer": FOOTER,
            "fields": create_fields(tweet)
        }

        if tweet.images:
            embed["image"] = {
                "url": tweet.images[0]
            }

        if not tweet.retweeted:
            embed["url"] = tweet.link.replace("nitter.net", "twitter.com").split("#")[0]

        return embed

    def post_to_webhook(self, tweets: list[Tweet]) -> None:
        pings = [f"<@&{r}>" for r in self.ping_roles]

        params = {
            "content": "".join(pings),
            "embeds": [self.create_tweet_embed(x) for x in tweets],
            "username": f"@{self.username} - Twitter",
            "avatar_url": self.pfp
        }

        resp = requests.post(
            url=self.url,
            json=params
        )

        if resp.status_code > 299:
            raise Exception(
                f"Failed to submit to webhook, status: {resp.status_code}; {resp.text}"
            )
