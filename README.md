# Nitter Discord webhook

This repo provides the code to locally host an instance of a Nitter RSS feed
crawler that posts new tweets to a selected Discord (or compatible) webhook,
with the option to ping one or several roles, adjustable time delays between
fetches and no reliance on the the official Twitter API.

## Setup

To setup the crawler:

- Download or `git clone` the repo
- Move the `example-config.toml` file to `config.toml` and edit it according to
  the comments provided.
- Run `pip install -r requirements.txt` to install all required packages.

Once this is finished you can run `python main.py` and your webhook should come
to life with the tweets of the account you selected in the `config.toml`.
