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

import datetime
import gzip
import io
import logging
import os.path
from sys import exit

from django.conf import settings
from django.core.management.base import BaseCommand
from rest_framework.status import HTTP_200_OK

import requests


class Command(BaseCommand):
    help = "Download GeoIP files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            "-o",
            help="Output directory for the files, defaults to settings.GEOIP_PATH",
            default=settings.GEOIP_PATH,
        )

    def download_file(self, basename, max_lookback=datetime.timedelta(days=180)):
        date = datetime.date.today()
        range_end = datetime.date.today() - max_lookback

        while date > range_end:
            date_str = date.strftime("%Y-%m")
            date -= datetime.timedelta(days=31)
            url = f"https://download.db-ip.com/free/{basename}-{date_str}.mmdb.gz"
            logging.info("Trying the download at %s", url)
            resp = requests.get(url)

            if resp.status_code != HTTP_200_OK:
                continue

            return io.BytesIO(resp.content)

    def download_and_extract(self, basename, output_file):

        file = self.download_file(basename)

        if not file:
            logging.error("Could not download city file, aborting...")
            exit(1)

        decompressed_file = gzip.open(file)
        with open(output_file, "wb") as f:
            f.write(decompressed_file.read())

    def handle(self, output, *args, **kwargs):
        logging.basicConfig(level=logging.INFO)
        files = {
            os.path.join(output, settings.GEOIP_CITY): "dbip-city-lite",
            # Not required for now
            # os.path.join(output, settings.GEOIP_COUNTRY): "dbip-country-lite",
        }
        for dst, basename in files.items():
            self.download_and_extract(basename, dst)
