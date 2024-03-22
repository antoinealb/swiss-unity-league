#!/usr/bin/env python3
"""
Simple example for the API of unityleague.ch, showing how to create an event.
"""

import argparse
import enum
import getpass
import json

import requests


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--instance",
        default="https://playground.unityleague.ch",
        help="Address of the Unity League instance to use.",
    )
    parser.add_argument("--username", "-u", help="Username to use", required=True)
    parser.add_argument(
        "--password",
        "-p",
        help="Password, if not provided will be asked on the commandline.",
    )

    return parser.parse_args()


def get_api_token(instance: str, username: str, password: str) -> str:
    """Fetch the API key that can then be used on follow up requests."""
    url = f"{instance}/api/auth/"
    data = {"username": username, "password": password}
    resp = requests.post(url, json=data)
    resp.raise_for_status()
    return resp.json()["token"]


def get_events_for_result_upload(instance: str, token: str) -> list[tuple[str, str]]:
    url = f"{instance}/api/events/need_results/"
    headers = {"Authorization": f"Token {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()

    return [(event["name"], event["api_url"]) for event in resp.json()]


class SingleEliminationResult(enum.IntEnum):
    """Enum representing how far in the top8 a player went.

    The API expects numbers, this enum allows the example to be more readable.
    """

    WINNER = 1
    FINALIST = 2
    SEMI_FINALIST = 4
    QUARTER_FINALIST = 8


def upload_results(event_url: str, token: str):
    # Simple example with Top 4
    example_results = [
        {
            "player": "Darth Vader",
            "win_count": 3,
            "draw_count": 2,
            "loss_count": 0,
            "single_elimination_result": SingleEliminationResult.WINNER,
        },
        {
            "player": "Obiwan Kenobi",
            "win_count": 3,
            "draw_count": 1,
            "loss_count": 1,
            "single_elimination_result": SingleEliminationResult.FINALIST,
        },
        {
            "player": "Padme Amidala",
            "win_count": 3,
            "draw_count": 1,
            "loss_count": 1,
            "single_elimination_result": SingleEliminationResult.SEMI_FINALIST,
        },
        {
            "player": "R2D2",
            "win_count": 3,
            "draw_count": 2,
            "loss_count": 0,
            "single_elimination_result": SingleEliminationResult.FINALIST,
        },
        {
            "player": "Han Solo",
            "win_count": 2,
            "draw_count": 2,
            "loss_count": 0,
            "single_elimination_result": None,
        },
        {
            "player": "Yoda",
            "win_count": 0,
            "draw_count": 0,
            "loss_count": 2,
            "single_elimination_result": None,
        },
        {
            "player": "Qui-Gon Jinn",
            "win_count": 0,
            "draw_count": 0,
            "loss_count": 1,
            "single_elimination_result": None,
        },
    ]

    headers = {"Authorization": f"Token {token}"}
    resp = requests.patch(
        url=event_url,
        json={"results": example_results},
        headers=headers,
    )
    resp.raise_for_status()


def get_user_name(instance: str, token: str) -> str:
    # The /me URL returns information about the logged in user
    url = f"{instance}/api/organizers/me"
    headers = {"Authorization": f"Token {token}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["name"]


def main():
    args = parse_args()

    password = args.password or getpass.getpass("password:")

    print("Getting API token..")
    token = get_api_token(args.instance, args.username, password)
    print(f"Got API token: {token[:5]}[...]")

    name = get_user_name(args.instance, token)
    print(f"Welcome '{name}', getting your events!")

    events = get_events_for_result_upload(args.instance, token)
    for name, url in events:
        print(f"{name} ({url})")

    if not events:
        print(
            "No events waiting for results, maybe create one (Regional), and come back?"
        )
        return
    name, url = events[0]
    print(f"Uploading for {name}")
    upload_results(url, token)


if __name__ == "__main__":
    main()
