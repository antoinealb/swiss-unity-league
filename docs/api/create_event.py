#!/usr/bin/env python3
# Copyright 2024 Leonin League
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Simple example for the API of unityleague.ch, showing how to create an event.
"""

import argparse
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


def create_example_event(instance: str, token: str):
    data = {
        "name": "API Christmas Event",
        "date": "2024-12-25",
        "start_time": "13:00:00",
        "end_time": "20:00:00",
        "format": "LEGACY",
        "category": "PREMIER",
        "url": "https://test.example",
        "description": "This is going to be <b>very</b> cool!",
    }
    headers = {"Authorization": f"Token {token}"}
    url = f"{instance}/api/events/"
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()


def main():
    args = parse_args()

    password = args.password or getpass.getpass("password:")

    print("Getting API token..")
    token = get_api_token(args.instance, args.username, password)
    print(f"Got API token: {token[:5]}[...]")

    print("Creating example event...")
    event = create_example_event(args.instance, token)
    print(json.dumps(event, indent=4))


if __name__ == "__main__":
    main()
