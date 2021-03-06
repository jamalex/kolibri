import os

import atexit
import multiprocessing
import cherrypy
from django.conf import settings
from django.core.management import call_command
from kolibri.content.utils import paths
from kolibri.content.utils.annotation import update_channel_metadata_cache
from kolibri.deployment.default.wsgi import application


def start_background_workers():
    p = multiprocessing.Process(target=call_command, args=("qcluster",))

    # note: atexit normally only runs when python exits normally, aka doesn't
    # exit through a signal. However, this function gets run because cherrypy
    # catches all the various signals, and runs the atexit callbacks.
    atexit.register(p.terminate)

    p.start()


def start():

    # TODO(aronasorman): move to install/plugin-enabling scripts, and remove from here
    call_command("collectstatic", interactive=False)
    call_command("collectstatic_js_reverse", interactive=False)
    call_command("migrate", interactive=False, database="default")
    call_command("migrate", interactive=False, database="ormq")

    # start the qcluster process
    start_background_workers()

    update_channel_metadata_cache()

    run_server()

def run_server():

    # Mount the application
    cherrypy.tree.graft(application, "/")

    serve_static_dir(settings.STATIC_ROOT, settings.STATIC_URL)
    serve_static_dir(settings.CONTENT_DATABASE_DIR, paths.get_content_database_url("/"))
    serve_static_dir(settings.CONTENT_STORAGE_DIR, paths.get_content_storage_url("/"))

    # Unsubscribe the default server
    cherrypy.server.unsubscribe()

    cherrypy.config.update({'server.socket_host': "0.0.0.0",
                            'server.socket_port': 8080,
                            'server.thread_pool': 30,
                            'log.screen': True})

    # Instantiate a new server object
    server = cherrypy._cpserver.Server()

    # Subscribe this server
    server.subscribe()

    # Start the server engine (Option 1 *and* 2)

    cherrypy.engine.start()
    cherrypy.engine.block()

def serve_static_dir(root, url):

    static_handler = cherrypy.tools.staticdir.handler(
        section="/",
        dir=os.path.split(root)[1],
        root=os.path.abspath(os.path.split(root)[0])
    )
    cherrypy.tree.mount(static_handler, url)
