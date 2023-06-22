import datetime, requests, re
from typing import Optional

PATTERN = r"document\.cookie\s*=\s*\"([^\"]+)\"|document\.cookie\s*=\s*\'([^\']+)\'|document\.cookie\s*=\s*\`([^\`]+)\`"


def parse_pair(pair: str) -> tuple[str, Optional[str]]:
    stripped = pair.strip()
    if not "=" in stripped:
        return stripped, None

    split = [x.strip() for x in stripped.split("=")]

    if len(split) != 2:
        raise ValueError(f"Invalid cookie: {stripped}")

    return tuple(split)


def parse_cookies(cookies: str) -> dict[str, Optional[str]]:
    return dict(parse_pair(x) for x in cookies.split(";"))


def findin_cookies(html: str, *args: str) -> list[Optional[str]]:
    match = re.findall(PATTERN, html, re.UNICODE | re.MULTILINE)
    cookies = parse_cookies(";".join(x[0] for x in match))
    return [cookies.get(x) for x in args]


def request_token(ua: str, recursion: int = 0) -> tuple[str, str]:
    req = requests.get(
        "https://twitter.com",
        headers={"User-Agent": ua}
    )

    gt = req.cookies.get("gt")
    ma = req.cookies.get("Max-Age")

    if gt and ma:
        return gt, ma

    gt, ma = findin_cookies(req.text, "gt", "Max-Age")

    if gt and ma:
        return gt, ma

    if recursion > 10:
        raise Exception("Guest Token unreachable")
    else:
        return request_token(ua, recursion + 1)


class GT:
    ua: str
    token: str
    expire: datetime.datetime

    def __init__(self, ua: str) -> None:
        self.ua = ua
        self.__new_token()

    def __new_token(self) -> str:
        gt, ma = request_token(self.ua)
        self.token = gt

        td = datetime.timedelta(seconds=int(ma))
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        self.expire = now + td

        return gt

    def get_token(self) -> str:
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if now < self.expire:
            return self.token
        else:
            return self.__new_token()


if __name__ == "__main__":
    gt = GT("Mozilla 5.0")

    print(gt.get_token())
