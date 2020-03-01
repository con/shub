import asyncio

from sanic import Sanic
from sanic.log import logger, error_logger, access_logger
from sanic import response
from sanic_cors import CORS, cross_origin
import requests
from sanic.exceptions import NotFound

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

@app.route("/dandiset/<dataset:int>")
async def get_dataset_info(request, dataset):
    """Redirect to gui with retrieved folder ID
    """
    req = requests.get(
        f"https://girder.dandiarchive.org/api/v1/dandi?id={dataset:06d}")
    if req.reason == 'OK':
        json_info = req.json()
        if json_info is not None:
            id = json_info['_id']
            return response.redirect(f"https://gui.dandiarchive.org/#/folder/{id}")
    return NotFound(f"dandi:{dataset} not found.")

@app.route("/dandiset/<dataset:int>/<version>")
async def get_dataset_version_info(request, dataset, version):
    req = requests.get(
        f"https://girder.dandiarchive.org/api/v1/dandi?id={dataset:06d}")
    if req.reason == 'OK':
        json_info = req.json()
        if json_info is not None:
            id = json_info['_id']
            return response.redirect(f"https://gui.dandiarchive.org/#/folder/{id}")
    return NotFound(f"dandi:{dataset}/{version} not found.")

if __name__ == "__main__":
    logger.info("Starting backend")
    app.run(host="0.0.0.0", port=8080)