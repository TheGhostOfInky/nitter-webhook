<!-- # Twitter Discord webhook

This repo provides the code to locally host an instance of a Twitter crawler
that posts new tweets (including replies) to a selected Discord (or compatible)
webhook, with the option to ping one or several roles, adjustable time delays
between fetches and no reliance on the pricey official API.

## Setup

To setup the crawler:

- Download or `git clone` the repo
- Move the `example-config.toml` file to `config.toml` and edit it according to
  the comments provided.
- Run `pip install -r requirements.txt` to install all required packages.
- Setup playwright if you did not previously have it installed on your system by
  running `playwright install`, make sure your pip scripts folder is in `PATH`
  beforehand.
- After playwright is setup, run `python scrape.py` on the root to generate the
  `variables.toml` file.

Once this is finished you can run `python main.py` and your webhook should come
to life with the tweets of the account you selected in the `config.toml`. -->

# Archive ONLY

Due to Twitter changing policy to prevent guest users (not logged in) from
viewing tweets it is no longer possible to scrape tweets without botting an
account, which is more risk than I personally believe is worth so this is no
longer functional
