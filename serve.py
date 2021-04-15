"""
Implements minimal API necessary for singularity client to be
able to fetch singularity images.

It will be reverse proxied for https://singularity-hub.org/api/
(so any other component will be handled at web server level)

TODO: may be we should provide redirect also for
/collections/<id>
to go to specific folder within datalad dataset???
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
# it is difference since this is direct url without web ui
TOP_URL = "https://datasets.datalad.org/repronim"

# TODO: do establish logging for deployed instance

production = False # "DEV628cc89a6444" not in os.environ
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

#
# Since Yarik knows no sanic etc, he would just populate
# this data structure to be used in the endpoints
#
_data_ = {}

headers = {
    "Content-Type": "application/json",
}

"""
currently from singularity-hub
< HTTP/1.1 200 OK
< Server: nginx/1.13.5
< Date: Wed, 14 Apr 2021 22:48:02 GMT
< Content-Type: application/json
< Content-Length: 1156
< Connection: keep-alive
< Vary: Accept, Cookie
< Allow: GET, HEAD, OPTIONS
< X-Frame-Options: SAMEORIGIN
"""
@app.route("container/<org:[^/]+>/<repo:[^/:]+><tag:.*>", methods=["GET", "HEAD"])
async def goto_dandiset(request, org, repo, tag):
    """Parse/handle the query
    """
    try:
        name = f"{org}/{repo}"
        collection = _data_['records'].get(name, None)
        # debug
        # return response.json(
        #     {
        #         "name": name,
        #         "org": org,
        #         "repo": repo,
        #         "collection": collection,
        #         "found": bool(collection)},
        #     headers=headers
        # )
        if collection:
            if tag and tag.startswith(':'):
                tag = tag[1:]
            if not tag:
                tag = 'latest'
            if tag in collection:
                return response.json(collection[tag], headers=headers)
        return response.json(
            {"detail": "Not found."},
            status=404,
            headers=headers
        )
    except Exception as exc:
        return response.json(
            {"detail": f"Exception {exc}"},
            status=500,
            headers=headers
        )

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


import click
import json


@click.command()
@click.argument("json_path", type=click.Path(exists=True, file_okay=True))
def main(json_path):
    logger.info("Loading")
    with open(json_path) as f:
        raw = json.load(f)

    # prepare target complete records to return
    logger.info("Preparing final records")
    # to ease comparison etc
    fields_order = 'id', 'name', 'branch', 'commit', 'tag', 'version', 'size_mb', 'image', 'build_date'
    _data_['records'] = recs = {}
    for name, files in raw.items():
        recs[name] = res = {}  # tag: { ready image record }
        for f in files:
            rec = f.copy()
            rec['name'] = name
            rec['image'] = f"{TOP_URL}/{rec.pop('file')}"
            # order (and "pop") the fields to match the one we observe with
            # stock singularity hubwhich we just eagerly got but not needed
            rec = {
                _: rec[_] for _ in fields_order if _ in rec
            }
            # what lookups are "supported
            for id_field in 'tag', 'version':
                id_ = f[id_field]
                if id_ in res:
                    # replace only if build_date is after a known one
                    # due to use of iso I think string comparison should be
                    # good enough
                    if res[id_]['build_date'] > rec['build_date']:
                        continue  # we do not replace
                res[id_] = rec

    # strip away all build_date's
    for _, tags in recs.items():
        for _, r in tags.items():
            # could be already gone since we bind the same record across
            # multiple tags
            r.pop('build_date', None)

    logger.info("Starting backend")
    app.run(host="0.0.0.0", port=5003)


if __name__ == "__main__":
    main()