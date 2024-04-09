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


class OracleRouter:
    """
    A router that sends all queries for oracle models to a separate DB.

    The reason for doing this is that the oracle DB is read only, and generated
    from an external Scryfall bulk. We don't want this database to be backed up
    and we ship it with the Docker image.
    """

    route_app_labels = {"oracle"}
    route_db = "oracle"

    def db_for_read(self, model, **hints):
        """
        Attempts to read Oracle data goes to the Oracle DB.
        """
        if model._meta.app_label in self.route_app_labels:
            return self.route_db
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return self.route_db
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure that Oracle data only goes in Oracle DB.
        """
        if app_label in self.route_app_labels:
            return db == self.route_db
        else:
            return db != self.route_db
