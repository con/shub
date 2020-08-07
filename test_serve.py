import pytest
from   serve import app

NEXIST_DANDI_ID = "999999"

@pytest.mark.parametrize('req_url,resp_url', [
    ("/", "https://gui.dandiarchive.org/"),
    ("/about", "https://www.dandiarchive.org"),
    ("/dandiset", "https://gui.dandiarchive.org/#/dandiset"),
    (
        "/dandiset/000003",
        "https://gui.dandiarchive.org/#/dandiset/5e6eb2b776569eb93f451f8d",
    ),
    (
        "/dandiset/000003/0.20200703.1040",
        "https://gui.dandiarchive.org/#/dandiset/5e6eb2b776569eb93f451f8d",
    ),
])
def test_redirect(req_url, resp_url):
    _, r = app.test_client.get(req_url)
    r.raise_for_status()
    assert r.url == resp_url

@pytest.mark.parametrize('req_url,resp_url', [
    (
        "/dandiset/000003",
        "https://gui.dandiarchive.org/#/dandiset/5e6eb2b776569eb93f451f8d",
    ),
    (
        "/dandiset/000003/0.20200703.1040",
        "https://gui.dandiarchive.org/#/dandiset/5e6eb2b776569eb93f451f8d",
    ),
])
def test_redirect_head(req_url, resp_url):
    _, r = app.test_client.head(req_url)
    r.raise_for_status()
    assert r.headers["Location"] == resp_url
    assert r.status_code == 302
    assert r.text == ''

def test_redirect_nonexistent_dandiset():
    _, r = app.test_client.get(f"/dandiset/{NEXIST_DANDI_ID}")
    assert r.status_code == 404
    assert r.text == f"dandi:{NEXIST_DANDI_ID} not found."

def test_redirect_nonexistent_dandiset_version():
    _, r = app.test_client.get(f"/dandiset/{NEXIST_DANDI_ID}/0.20200703.1040")
    assert r.status_code == 404
    assert r.text == f"dandi:{NEXIST_DANDI_ID}/0.20200703.1040 not found."
