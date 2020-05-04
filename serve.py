import asyncio
import os
from sanic import Sanic
from sanic.log import logger
from sanic import response
from sanic_cors import CORS
import requests

production = 'DEV628cc89a6444' not in os.environ
sem = None
basedir = os.environ["HOME"] if production else os.getcwd()
logdir = os.path.join(basedir, "redirector")
if not os.path.exists(logdir):
    os.makedirs(logdir, exist_ok=True)
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
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": 'D',
            "interval": 7,
            "backupCount": 10,
            'filename': os.path.join(logdir, "console.log"),
            "formatter": "generic",
        },
        "error_consolefile": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": 'D',
            "interval": 7,
            "backupCount": 10,
            'filename': os.path.join(logdir, "error.log"),
            "formatter": "generic",
        },
        "access_consolefile": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "when": 'D',
            "interval": 7,
            "backupCount": 10,
            'filename': os.path.join(logdir, "access.log"),
            "formatter": "access",
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


@app.listener("before_server_start")
async def init(app, loop):
    global sem
    sem = asyncio.Semaphore(100)


@app.route("/")
async def main(request):
    return response.redirect("https://gui.dandiarchive.org/")


@app.route("/about")
async def about(request):
    return response.redirect("https://www.dandiarchive.org")


@app.route("/dandiset")
async def get_public_dashboard(request):
    """Redirect to gui draft collection
    """
    return response.redirect("https://gui.dandiarchive.org/#/dandiset")


@app.route("/portal")
async def about(request):
    return response.redirect("https://gui.dandiarchive.org")


@app.route("/dandiset/<dataset:int>")
async def get_dataset_info(request, dataset):
    """Redirect to gui with retrieved folder ID
    """
    req = requests.get(
        f"https://girder.dandiarchive.org/api/v1/dandi/{dataset:06d}")
    if req.reason == 'OK':
        json_info = req.json()
        if json_info is not None:
            id = json_info['_id']
            return response.redirect(f"https://gui.dandiarchive.org/#/dandiset/{id}")
    return response.text(f"dandi:{dataset:06d} not found.", status=404)


@app.route("/dandiset/<dataset:int>/<version>")
async def get_dataset_version_info(request, dataset, version):
    req = requests.get(
        f"https://girder.dandiarchive.org/api/v1/dandi/{dataset:06d}")
    if req.reason == 'OK':
        json_info = req.json()
        if json_info is not None:
            id = json_info['_id']
            return response.redirect(f"https://gui.dandiarchive.org/#/dandiset/{id}")
    return response.text(f"dandi:{dataset:06d}/{version} not found.", status=404)

if __name__ == "__main__":
    logger.info("Starting backend")
    app.run(host="0.0.0.0", port=8080)
