import datetime, pytz, requests
from bs4 import BeautifulSoup, ResultSet, element
from urllib.parse import unquote, quote
from typing import Optional, cast, TypedDict

FMT = r"%a, %d %b %Y %H:%M:%S %Z"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


class InstanceKey(TypedDict):
    url: str
    domain: str
    points: int
    rss: bool
    recent_pings: list[int]
    ping_max: int
    ping_min: int
    ping_avg: int
    version: str
    version_url: str
    healthy: bool
    last_healthy: str
    is_upstream: bool
    is_latest_version: bool
    is_bad_host: bool
    country: str
    recent_checks: list[tuple[str, bool]]
    healthy_percentage_overall: int
    connectivity: Optional[str]


class APIResponse(TypedDict):
    hosts: list[InstanceKey]
    last_update: str
    latest_commit: str


def check_instance_health(instance: InstanceKey) -> bool:
    if instance["connectivity"] is None:
        return False

    if not instance["healthy"]:
        return False

    if not instance["rss"]:
        return False

    if instance["is_bad_host"]:
        return False

    return True


def get_auto_instance() -> tuple[str, str]:
    resp = cast(APIResponse, requests.get(
        "https://status.d420.de/api/v1/instances", headers=HEADERS
    ).json())

    raw_instances = resp["hosts"]

    rss_instances = [x for x in raw_instances if check_instance_health(x)]

    return rss_instances[0]["url"], rss_instances[0]["domain"]


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


def is_ping(href: str, text: str) -> Optional[str]:
    if not text.startswith("@"):
        return None

    split = text.split("@")
    if len(split) != 2:
        return None

    ping = split[1]

    if ping not in href:
        return None

    return f"[@{ping}](https://x.com/{quote(ping)})"


def is_hashtag(href: str, text: str) -> Optional[str]:
    if not text.startswith("#") or "search?q=#" not in href:
        return None

    split = text.split("#")

    if len(split) != 2:
        return None

    hashtag = split[1]

    if hashtag not in href:
        return None

    return f"[#{hashtag}](https://x.com/hashtag/{quote(hashtag)})"


def parse_desc(desc: str) -> tuple[str, list[str], list[str]]:
    soup = BeautifulSoup(unquote(desc), "lxml")

    raw_img = [src for i in soup.find_all("img") if (
        src := parse_prop(cast(element.Tag, i.extract()), "src")
    )]

    img = [y[1] for x in raw_img if len(y := x.split("/media/")) == 2]

    a_elms = soup.find_all("a")
    links = []

    for elm in a_elms:
        href, a_text = cast(tuple[str, str], (elm.get("href"), elm.text))

        if not href:
            continue

        if not a_text:
            a_text = ""

        if ping := is_ping(href, a_text):
            elm.replace_with(ping)
            continue

        if hashtag := is_hashtag(href, a_text):
            elm.replace_with(hashtag)
            continue

        links.append(href)
        elm.extract()

    txt = [cast(str, x.text) for x in soup.find_all("p")]

    return "\n".join(txt), links, img


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

    def __init__(self, name: str, instance: str) -> None:
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
    instance = get_auto_instance() or "nitter.net"
    ts = TweetStream("elonmusk", instance[0])

    print(*ts.tweets, sep="\n")
