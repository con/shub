"""
Implements minimal API necessary for singularity client to be
able to fetch singularity images.

It will be reverse proxied for https://singularity-hub.org/api/
(so any other component will be handled at web server level)
"""

import asyncio
import re
import os
from sanic import Sanic
from sanic.log import logger
from sanic import response
from sanic_cors import CORS
import requests

# TODO: move from repronim to hub
GOTO_URL = "https://datasets.datalad.org/?dir=/repronim"

# TODO: do establish logging for deployed instance

production = True # "DEV628cc89a6444" not in os.environ
sem = None
basedir = os.getcwd() # environ["HOME"] if production else os.getcwd()
logdir = os.path.join(basedir, "logs")
if not os.path.exists(logdir):
    os.makedirs(logdir, exist_ok=True)

handler_dict = {
    "class": "logging.handlers.TimedRotatingFileHandler",
    "when": "D",
    "interval": 7,
    "backupCount": 10,
    "formatter": "generic",
}
LOG_SETTINGS = dict(
    version=1,
    disable_existing_loggers=False,
    loggers={
        "sanic.root": {"level": "INFO", "handlers": ["consolefile"]},
        "sanic.error": {
            "level": "INFO",
            "handlers": ["error_consolefile"],
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": "INFO",
            "handlers": ["access_consolefile"],
            "propagate": True,
            "qualname": "sanic.access",
        },
    },
    handlers={
        "consolefile": {
            **handler_dict,
            **{"filename": os.path.join(logdir, "console.log")},
        },
        "error_consolefile": {
            **handler_dict,
            **{"filename": os.path.join(logdir, "error.log")},
        },
        "access_consolefile": {
            **handler_dict,
            **{"filename": os.path.join(logdir, "access.log")},
        },
    },
    formatters={
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
        "access": {
            "format": "%(asctime)s - (%(name)s)[%(levelname)s][%(host)s]: "
            + "%(request)s %(message)s %(status)d %(byte)d",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
    },
)

if production:
    app = Sanic("redirector", log_config=LOG_SETTINGS)
else:
    app = Sanic("redirector")
CORS(app)


def make_header(url):
    import time

    gmtnow = time.strftime("%a, %d %b %Y %I:%M:%S %p %Z", time.gmtime())
    header = {
        "location": url,
        "content-type": "text/plain;charset=UTF-8",
        "content-length": 0,
        "date": gmtnow,
        "alt-svc": "clear",
    }
    return header


@app.listener("before_server_start")
async def init(app, loop):
    global sem
    sem = asyncio.Semaphore(100)


@app.route("/", methods=["GET"])
async def main(request):
    return response.redirect(GOTO_URL)


@app.route("container/<collection>/<container>", methods=["GET", "HEAD"])
async def goto_dandiset(request, collection, container):
    """Parse/handle the query
    """
    return response.json({
            "collection": collection
        })

"""
    if not re.fullmatch(dandiset_identifier_regex, dataset):
        return response.text(f"{dataset}: invalid Dandiset ID", status=400)
    req = requests.get(f"{GIRDER_LOCAL_URL}/api/v1/dandi/{dataset}")
    if req.reason == "OK":
        url = f"{GUI_URL}/#/dandiset/{dataset}/draft"
        if request.method == "HEAD":
            return response.html(None, status=302, headers=make_header(url))
        return response.redirect(url)
    return response.text(f"dandi:{dataset} not found.", status=404)
"""

if __name__ == "__main__":
    logger.info("Starting backend")
    app.run(host="0.0.0.0", port=8080)
