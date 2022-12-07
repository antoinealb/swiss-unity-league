#!/usr/bin/env python3
"""
Imports all of our 2022 tournaments in the league website.

Used for testing mostly.
"""

import argparse
import os
import requests
import getpass
import collections
from datetime import date
from bs4 import BeautifulSoup

ExistingTournament = collections.namedtuple(
    "ExistingTournament", ["name", "date", "number"]
)


EXISTING_TOURNAMENTS = [
    # fmt: off
    ExistingTournament("MTG@DuBischDra Modern 1k #1", date(2021, 7, 25),  "https://aetherhub.com/Tourney/RoundTourney/8783"),
    ExistingTournament("MTG@DuBischDra Modern 1k #2", date(2021, 9, 12),  "https://aetherhub.com/Tourney/RoundTourney/9462"),
    ExistingTournament("MTG@DuBischDra Modern 1k #3", date(2022, 3, 13),  "https://aetherhub.com/Tourney/RoundTourney/11231"),
    # No tournament #4, it was a team event
    ExistingTournament("MTG@DuBischDra Limited 1k #5", date(2021, 10, 2), "https://aetherhub.com/Tourney/RoundTourney/13924"),
    ExistingTournament("MTG@DuBischDra Modern 1k #6", date(2022, 10, 9),  "https://aetherhub.com/Tourney/RoundTourney/13923"),
    # fmt: on
]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instance",
        "-i",
        default="https://leoninleague.ch",
        help="URL of the root of the website, default https://leoninleague.ch",
    )
    parser.add_argument(
        "--username",
        "-u",
        help="Username to use, defaults to the login username of the person running this script",
        default=os.getlogin(),
    )
    parser.add_argument(
        "--password",
        "-p",
        help="Password for the user, if not provided it will be asked on the CLI",
    )

    return parser.parse_args()


def post_with_csrf(session, url, data):
    session.get(url)
    csrftoken = session.cookies["csrftoken"]
    data["csrfmiddlewaretoken"] = session.cookies["csrftoken"]
    return session.post(url, data=data)


def login(session, instance, username, password):
    login_url = f"{instance}/accounts/login/"
    data = {
        "username": username,
        "password": password,
    }
    r = post_with_csrf(session, login_url, data)
    r.raise_for_status()


def create_tournament(session, instance, name, date, url):
    create_url = f"{instance}/events/create"

    if "limited" in name.lower():
        format = "LIMITED"
    else:
        format = "MODERN"
    data = {
        "name": name,
        "url": url,
        "date": date.strftime("%Y-%m-%d"),
        "format": format,
        "category": "PREMIER",
    }

    r = post_with_csrf(session, create_url, data)
    r.raise_for_status()


def upload_results(session, instance, name, url):
    upload_url = f"{instance}/results/create/aetherhub"

    r = session.get(upload_url)
    r.raise_for_status()
    soup = BeautifulSoup(r.content.decode(), features="html.parser")

    for o in soup.find(id="id_event").find_all("option"):
        if name in o.text:
            value = o["value"]
            break
    else:
        raise RuntimeError("No event with the correct name found")

    data = {
        "url": url,
        "event": value,
    }

    r = post_with_csrf(session, upload_url, data)
    r.raise_for_status()


def main():
    args = parse_args()

    if args.password:
        password = args.password
    else:
        password = getpass.getpass(f"Password for {args.username}:")

    with requests.session() as session:
        login(session, args.instance, args.username, password)

    for name, date, url in EXISTING_TOURNAMENTS:
        create_tournament(session, args.instance, name, date, url)
        upload_results(session, args.instance, name, url)


if __name__ == "__main__":
    main()
