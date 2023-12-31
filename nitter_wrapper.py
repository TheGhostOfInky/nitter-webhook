import datetime, pytz, requests
from bs4 import BeautifulSoup, ResultSet, element
from urllib.parse import unquote
from typing import Optional, cast

FMT = r"%a, %d %b %Y %H:%M:%S %Z"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


def parse_elm(res: element.Tag | element.NavigableString | None) -> str:
    if res is None:
        return "Missing"

    return res.text


def parse_date(res: element.Tag | element.NavigableString | None) -> datetime.datetime:
    if res is None:
        raise ValueError("No creation time found")

    text = res.text
    tz = pytz.timezone(text.split(" ")[-1])
    dt = datetime.datetime.strptime(text, FMT)

    return tz.localize(dt)


def parse_prop(elm: element.Tag, prop: str) -> Optional[str]:
    props = elm.get(prop)

    if props is None:
        return

    if isinstance(props, list):
        return props[0]

    return props


def parse_desc(desc: str) -> tuple[str, list[str], list[str]]:
    soup = BeautifulSoup(unquote(desc), "lxml")

    img = [src for i in soup.find_all("img") if (
        src := parse_prop(cast(element.Tag, i.extract()), "src")
    )]

    link = [href for l in soup.find_all("a") if (
        href := parse_prop(cast(element.Tag, l.extract()), "href")
    )]

    txt = [cast(str, x.text) for x in soup.find_all("p")]

    return "\n".join(txt), link, img


class Tweet:
    title: str
    creator: str
    link: str
    time: datetime.datetime
    text: str
    urls: list[str]
    images: list[str]
    retweeted: bool

    def __init__(self, elm: element.Tag) -> None:
        self.title = parse_elm(elm.find("title"))
        self.creator = parse_elm(elm.find("dc:creator"))
        self.link = parse_elm(elm.find("link"))

        self.time = parse_date(elm.find("pubDate"))

        raw_desc = elm.find("description")
        desc = ("", [], []) if raw_desc is None else parse_desc(raw_desc.text)
        self.text, self.urls, self.images = desc

        self.retweeted = self.title.startswith("RT")

    def __str__(self) -> str:
        dt = self.time.isoformat() if self.time is not None else "Missing"
        return f"Tweet(user={self.creator}, created={dt}, rt={self.retweeted}, links={len(self.urls)}, img={len(self.images)})"

    def __repr__(self) -> str:
        return str(self)


class TweetStream:
    tweets: list[Tweet]

    def __init__(self, name: str, instance="https://nitter.net") -> None:
        resp = requests.get(f"{instance}/{name}/rss", headers=HEADERS)
        if resp.status_code > 299:
            raise Exception(f"Got error response, code {resp.status_code}; {resp.text}")

        soup = BeautifulSoup(resp.text, "xml")
        items = cast(ResultSet[element.Tag], soup.find_all("item"))
        self.tweets = [Tweet(t) for t in items]

    def newer_than(self, dt: datetime.datetime, newest_first=False) -> list[Tweet]:
        filtered = [x for x in self.tweets if x.time > dt]

        return sorted(filtered, key=lambda x: x.time, reverse=newest_first)


__all__ = [
    "TweetStream",
    "Tweet"
]

if __name__ == "__main__":
    ts = TweetStream("elonmusk")

    print(*ts.tweets, sep="\n")
