from __future__ import with_statement

import uuid

from django.test.utils import override_settings
from django.utils.functional import wraps


class multiple_kolibri_servers(object):

    def __init__(self, count=2):
        self.server_count = count

    def __enter__(self):

        # spin up the servers
        self.servers = [KolibriServer() for i in range(self.server_count)]

        # calculate the DATABASE settings
        self.db_settings = {server.db_alias: {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": server.db_path,
            "OPTIONS": {"timeout": 100}}
            for server in self.servers}

        return self.servers

    def __exit__(self, typ, val, traceback):

        # make sure all the servers are shut down
        for server in self.servers:
            server.kill()

    def __call__(self, f):

        @wraps(f)
        def wrapper(*args, **kwargs):

            assert "servers" not in kwargs

            with self as servers, override_settings(DATABASES=self.db_settings):
                kwargs["servers"] = servers
                return f(*args, **kwargs)

        return wrapper


class KolibriServer(object):

    def __init__(self):
        self.db_alias = uuid.uuid4().hex
        self.db_path = "/tmp/mydir"
        print "Starting the server with db_alias", self.db_alias

    def kill(self):
        print "Killing the server with db_alias", self.db_alias
