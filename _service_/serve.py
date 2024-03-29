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
import click
import json
import os
from sanic import Sanic
from sanic.log import logger
from sanic import response
from sanic_cors import CORS

# TODO: move from repronim to hub
GOTO_URL = "https://datasets.datalad.org/?dir=/shub"
# it is difference since this is direct url without web ui
TOP_URL = "https://datasets.datalad.org/shub"

# TODO: do establish logging for deployed instance

production = "DEV628cc89a6444" not in os.environ
sem = None
basedir = os.getcwd() # environ["HOME"] if production else os.getcwd()
if production:
    logdir = '/srv/datasets.datalad.org/shub/logs'
    if not os.path.exists(logdir):
        os.makedirs(logdir, mode=0o700, exist_ok=True)
else:
    logdir = os.getcwd()  # should not even be used

handler_dict = {
    "class": "logging.handlers.TimedRotatingFileHandler",
    "when": "D",
    "interval": 7,
    "backupCount": 10000, # keep all
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
            **{"filename": os.path.join(logdir, "access.log"),
               "formatter": "access"},
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
    app = Sanic("shub-ro", log_config=LOG_SETTINGS)
else:
    app = Sanic("shub-ro")
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


@app.route("/<common:(|about|collections/my|labels)>", methods=["GET"])
async def main(request, common):
    return response.redirect(GOTO_URL)

# TODO: should we do something special about /labels etc?
# and also: /apps (could be datalad container?), and /tags

#
# Since Yarik knows no sanic etc, he would just populate
# this data structure to be used in the endpoints
#
_data_ = {}

headers = {
    "Content-Type": "application/json",
}


@app.route("collections/<pk:\d+>", methods=["GET", "HEAD"])
async def goto_container(request, pk):
    """Parse/handle the query
    """
    try:
        collection = (_data_['collections'].get(str(pk)) or {}).get('full_name')
        if collection:
            return response.redirect(f"{GOTO_URL}/{collection}")
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


@app.route("container/<org:[^/]+>/<repo:[^/:]+><tag:.*>", methods=["GET", "HEAD"])
async def goto_container(request, org, repo, tag):
    """Parse/handle the query
    """
    try:
        name = f"{org}/{repo}"
        collection = _data_['images'].get(name, None)
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


@click.command()
@click.argument("json_path", type=click.Path(exists=True, file_okay=True))
def main(json_path):
    logger.info("Loading")
    with open(json_path) as f:
        raw = json.load(f)

    assert set(raw) == {'images', 'collections'}
    _data_['collections'] = raw['collections']

    # prepare target complete records to return
    # Decided to keep this logic here so we could adjust
    # matching without needing to regenerate input file
    logger.info("Preparing final images records")
    # to ease comparison etc
    fields_order = 'id', 'name', 'branch', 'commit', 'tag', 'version', 'size_mb', 'image', 'build_date'
    recs = {}
    n_latest = 0
    for name, files in raw['images'].items():
        recs[name] = res = {}  # tag: { ready image record }
        latest = None
        for f in files:
            rec = f.copy()
            rec['name'] = name
            rec['image'] = f"{TOP_URL}/{rec.pop('file')}"
            # order (and "pop") the fields to match the one we observe with
            # stock singularity hub which we just eagerly got but not needed
            rec = {
                _: rec[_] for _ in fields_order if _ in rec
            }
            # paranoia
            if latest is not None and latest['build_date'] == rec['build_date']:
                raise RuntimeError(f"Found the one with the same date for {rec}")
            if latest is None or latest['build_date'] < rec['build_date']:
                latest = rec
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
        if 'latest' not in res:
            n_latest += 1
            if not production:
                print(f"{n_latest:02d}/{len(raw['images'])} {name}: "
                      f"adding detected 'latest' among {len(files)} records: "
                      f"tag {latest['tag']} from {latest['build_date']}")
            res['latest'] = latest

    # strip away all build_date's
    for _, tags in recs.items():
        for _, r in tags.items():
            # could be already gone since we bind the same record across
            # multiple tags
            r.pop('build_date', None)

    _data_['images'] = recs
    logger.info("Starting backend")
    app.run(host="0.0.0.0", port=5003)


if __name__ == "__main__":
    main()
