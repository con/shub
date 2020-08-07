import asyncio
import os
from sanic import Sanic
from sanic.log import logger
from sanic import response
from sanic_cors import CORS
import requests

GIRDER_URL = os.environ.get("GIRDER_URL", "https://girder.dandiarchive.org").rstrip('/')
GUI_URL = os.environ.get("GUI_URL", "https://gui.dandiarchive.org").rstrip('/')
REDIRECTOR_URL = os.environ.get("REDIRECTOR_URL", "https://dandiarchive.org").rstrip('/')

production = 'DEV628cc89a6444' not in os.environ
sem = None
basedir = os.environ["HOME"] if production else os.getcwd()
logdir = os.path.join(basedir, "redirector")
if not os.path.exists(logdir):
    os.makedirs(logdir, exist_ok=True)

handler_dict = {"class": "logging.handlers.TimedRotatingFileHandler",
                "when": 'D',
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
        "consolefile": {**handler_dict,
                        **{'filename': os.path.join(logdir, "console.log")}},
        "error_consolefile": {**handler_dict,
                              **{'filename': os.path.join(logdir, "error.log")}},
        "access_consolefile": {**handler_dict,
                               **{'filename': os.path.join(logdir, "access.log")}},
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
    header = {"location": url,
              "content-type": "text/plain;charset=UTF-8",
              "content-length": 0,
              "date": gmtnow,
              "alt-svc": "clear"}
    return header


@app.listener("before_server_start")
async def init(app, loop):
    global sem
    sem = asyncio.Semaphore(100)


@app.route("/", methods=['GET'])
async def main(request):
    return response.redirect(GUI_URL + '/')


@app.route("/about", methods=['GET'])
async def about(request):
    return response.redirect(REDIRECTOR_URL)


@app.route("/dandiset", methods=['GET'])
async def goto_public_dashboard(request):
    """Redirect to gui draft collection
    """
    return response.redirect(f"{GUI_URL}/#/dandiset")


@app.route("/dandiset/<dataset:int>", methods=['GET', 'HEAD'])
async def goto_dandiset(request, dataset):
    """Redirect to gui with retrieved folder ID
    """
    req = requests.get(
        f"{GIRDER_URL}/api/v1/dandi/{dataset:06d}")
    if req.reason == 'OK':
        json_info = req.json()
        if json_info is not None:
            id = json_info['_id']
            url = f"{GUI_URL}/#/dandiset/{id}"
            if request.method == "HEAD":
                return response.html(None, status=302, headers=make_header(url))
            return response.redirect(url)
    return response.text(f"dandi:{dataset:06d} not found.", status=404)


@app.route("/dandiset/<dataset:int>/<version>", methods=['GET', 'HEAD'])
async def goto_dandiset_version(request, dataset, version):
    req = requests.get(
        f"{GIRDER_URL}/api/v1/dandi/{dataset:06d}")
    if req.reason == 'OK':
        json_info = req.json()
        if json_info is not None:
            id = json_info['_id']
            url = f"{GUI_URL}/#/dandiset/{id}"
            if request.method == "HEAD":
                return response.html(None, status=302, headers=make_header(url))
            return response.redirect(url)
    return response.text(f"dandi:{dataset:06d}/{version} not found.", status=404)

if __name__ == "__main__":
    logger.info("Starting backend")
    app.run(host="0.0.0.0", port=8080)
