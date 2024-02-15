from typing import Any
from nitter_wrapper import Tweet
import requests, re

FOOTER = {
    "text": "Via 𝕏",
    "icon_url": "https://i.imgur.com/2YLLWrw.png"
}


def clean_urls(inp: str) -> str:
    sub = re.sub(r"https?:\/\/\S+", "", inp)
    return re.sub(r"@(\S+)", r"[@\1](https://x.com/\1)", sub)


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
    pings: str

    def __init__(self, url: str, username: str,
                 pfp: str, ping_roles: str | list[str],
                 ) -> None:
        self.username = username
        self.url = url
        self.pfp = pfp

        if isinstance(ping_roles, str):
            self.pings = f"<@&{ping_roles}>"
        else:
            self.pings = "".join([f"<@&{r}>" for r in ping_roles])

    def create_tweet_embed(self, tweet: Tweet, instance: str) -> dict:
        embed: dict[str, Any] = {
            "description": clean_urls(tweet.text),
            "timestamp": tweet.time.isoformat(),
            "color": 0xffffff,
            "footer": FOOTER,
            "fields": create_fields(tweet)
        }

        if tweet.images:
            embed["image"] = {
                "url": tweet.images[0]
            }

        if tweet.retweeted:
            embed["title"] = f"New retweet by @{self.username}"
        else:
            embed["title"] = f"New tweet by @{self.username}"
            embed["url"] = tweet.link\
                .replace(instance, "x.com")\
                .replace("http://", "https://")\
                .split("#")[0]

        return embed

    def post_to_webhook(self, tweets: list[Tweet], instance: str) -> None:
        params = {
            "content": self.pings,
            "embeds": [self.create_tweet_embed(x, instance) for x in tweets],
            "username": f"@{self.username} - 𝕏",
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
