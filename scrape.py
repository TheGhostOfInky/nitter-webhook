import asyncio, json, tomli_w
from typing import Any
from playwright.async_api import async_playwright, Route, Request
from urllib.parse import unquote

REMOVE_LIST = [
    "screen_name",
    "userId",
    "count"
]

stored_requests: list[Request] = []


async def routing(route: Route, request: Request) -> None:
    if "UserByScreenName" in request.url or "UserTweetsAndReplies" in request.url:
        stored_requests.append(request)
    await route.continue_()


def parse_json(input: str) -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(input)
    for x in REMOVE_LIST:
        if x in parsed:
            parsed.pop(x)

    return parsed


def parse_url(url: str) -> tuple[str, dict[str, dict[str, Any]]]:
    unqt = unquote(url)
    base, *vars = unqt.split("?")
    vars = [x.split("=") for x in "?".join(vars).split("&")]
    p_vars = {x[0]: parse_json(x[1]) for x in vars}
    full_url = base + "?" + "&".join(x + "={}" for x in p_vars.keys())
    return full_url, p_vars


def parse_requests(requests: list[Request], ua: str) -> None:
    urls = [parse_url(x.url) for x in requests]
    bt_set = set(x.headers.get("authorization") for x in requests)
    bt_key = bt_set.pop() or "Missing"

    ubsn = [x for x in urls if "UserByScreenName" in x[0]]
    utar = [x for x in urls if "UserTweetsAndReplies" in x[0]]

    final_vars = {
        "UserByScreenName": {
            "url": ubsn[0][0],
            **ubsn[0][1]
        },
        "UserTweetsAndReplies": {
            "url": utar[0][0],
            **utar[0][1]
        },
        "Bearer-Token": bt_key,
        "User-Agent": ua
    }

    with open("./variables.toml", "wb") as f:
        tomli_w.dump(final_vars, f)


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.route("**/*", routing)
        await page.goto("https://twitter.com/elonmusk/with_replies")
        ua: str = await page.evaluate("navigator.userAgent")
        await browser.close()
    parse_requests(stored_requests, ua)


if __name__ == "__main__":
    asyncio.run(main())
