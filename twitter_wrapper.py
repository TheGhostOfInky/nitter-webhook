import json, requests, datetime, os
from urllib.parse import quote
from html import unescape
from typing import Optional
from token_fetcher import GT
try:
    import tomllib
except ImportError:
    import tomli as tomllib

DIR_NAME = os.path.dirname(os.path.realpath(__file__))

with open(DIR_NAME + "/variables.toml", "rb") as f:
    vars = tomllib.load(f)

HEADERS = {
    "User-Agent": vars["User-Agent"],
    "Accept-Language": "en-US,en;q=0.5",
    "content-type": "application/json",
    "authorization": vars["Bearer-Token"],
    "x-twitter-client-language": "en-US",
    "x-twitter-active-user": "yes",
}

gt = GT(vars["User-Agent"])


def get_json(url: str, headers: dict) -> dict:
    response = requests.get(url, headers=headers)

    if response.status_code > 299:
        raise Exception(f"Error fetching tweets: {response.status_code}")

    content_type: str = response.headers.get("content-type", "unknown")
    if not content_type.lower().startswith("application/json"):
        raise Exception(
            f"Content type is {content_type}, expected application/json")

    return response.json()


class Tweet:
    def __init__(self, item: dict) -> None:
        raw_txt: str = item["full_text"]
        self.text: str = unescape(raw_txt)
        FORMAT = r"%a %b %d %H:%M:%S %z %Y"
        self.time = datetime.datetime.strptime(
            item["created_at"], FORMAT
        )
        self.__entities = item.get("entities")
        self.images = self.__parse_images()
        self.urls = self.__parse_urls()
        self.likes: int = item.get("favorite_count", 0)
        self.quotes: int = item.get("quote_count", 0)
        self.replies: int = item.get("reply_count", 0)
        self.retweets: int = item.get("retweet_count", 0)
        self.retweeted: bool = item.get("retweeted", False)
        self.id: str = item.get("id_str", "")

    def __parse_images(self) -> list[str]:
        if not isinstance(self.__entities, dict):
            return []

        media: Optional[list[dict]] = self.__entities.get("media")
        if not media:
            return []

        images: list[str] = []
        for elm in media:
            if elm.get("type", "") == "photo" and (photo := elm.get("media_url_https")):
                images.append(photo)

        return images

    def __parse_urls(self) -> list[str]:
        if not isinstance(self.__entities, dict):
            return []

        raw_urls: Optional[list[dict]] = self.__entities.get("urls")
        if not raw_urls:
            return []

        urls: list[str] = []
        for elm in raw_urls:
            url = elm.get("expanded_url")
            if url:
                urls.append(url)

        return urls

    def __str__(self) -> str:
        return f'Tweet(text="{self.text}", time={self.time.isoformat()})'

    def __repr__(self) -> str:
        return self.__str__()


class TweetStream:
    raw_data: Optional[list[dict]] = None
    tweets: list[Tweet] = []
    user_id: str

    def __get_id(self, name: str, headers: dict) -> str:
        variables = {
            "screen_name": name,
            **vars["UserByScreenName"]["variables"]
        }
        url = vars["UserByScreenName"]["url"].format(
            quote(json.dumps(variables)),
            quote(json.dumps(vars["UserByScreenName"]["features"]))
        )

        data = get_json(url, headers)
        return data["data"]["user"]["result"]["rest_id"]

    def __parse_items(self, content: dict) -> Optional[dict]:
        items: Optional[list[dict]] = content.get("items")

        if not items:
            return

        have_content = [cont for x in items if (cont := x["item"].get("itemContent"))]
        if have_content:
            return have_content[0]

    def __parse_item(self, item: dict) -> None:
        cnt = item["content"]
        if content := (cnt.get("itemContent") or self.__parse_items(cnt)):
            legacy_content = content["tweet_results"]["result"]["legacy"]
            self.tweets.append(Tweet(legacy_content))

    def __parse_data(self, data: list) -> None:
        for i in data:
            self.__parse_item(i)

    def __init__(self,
                 user_id: Optional[str] = None,
                 user_name: Optional[str] = None,
                 count: int = 20) -> None:

        if not user_id and not user_name:
            raise ValueError("No userId or userName provided")

        headers = {
            "x-guest-token": gt.get_token(),
            **HEADERS
        }

        if not user_id and user_name:
            user_id = self.__get_id(user_name, headers)

        variables = {
            "userId": user_id,
            "count": count,
            **vars["UserTweetsAndReplies"]["variables"]
        }

        url = vars["UserTweetsAndReplies"]["url"].format(
            quote(json.dumps(variables)),
            quote(json.dumps(vars["UserTweetsAndReplies"]["features"]))
        )

        data = get_json(url, headers)

        if data.get("data"):
            self.raw_data = data["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]

            for elm in self.raw_data:
                if elm["type"] == "TimelineAddEntries":
                    self.__parse_data(elm["entries"])

        elif data.get("errors"):
            err = "; ".join([x["message"] for x in data["errors"]])
            raise ValueError("Errors while recieving data:", err)

        else:
            raise Exception("Unknown error")

    def newer_than(self, time: datetime.datetime, newest_first=False) -> list[Tweet]:
        filtered = [x for x in self.tweets if x.time > time]

        return sorted(filtered, key=lambda x: x.time, reverse=newest_first)
