import asyncio

from sanic import Sanic
from sanic.log import logger, error_logger, access_logger
from sanic import response
from sanic.response import json, text
from sanic_cors import CORS, cross_origin

app = Sanic("redirector")
CORS(app)

@app.listener("before_server_start")
async def init(app, loop):
    app.sem = asyncio.Semaphore(100, loop=loop)


@app.route("/")
async def main(request):
    return response.redirect("https://gui.dandiarchive.org/")

@app.route("/about")
async def about(request):
    return response.redirect("https://www.dandiarchive.org")

@app.route("/<dataset:int>")
async def get_dataset_info(request, dataset):
    """Redirect to gui with retrieved folder ID
    """
    return response.json({"dataset": dataset, "version": "staged"})

@app.route("/<dataset:int>/<version>")
async def get_dataset_version_info(request, dataset, version):
    return response.json({"dataset": dataset, "version": version})

if __name__ == "__main__":
    logger.info("Starting backend")
    app.run(host="0.0.0.0", port=8080)
