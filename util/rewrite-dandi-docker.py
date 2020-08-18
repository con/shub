#!/usr/bin/python3
from pathlib import Path
from importlib_resources import as_file, files
from ruamel.yaml import YAML

yaml = YAML(typ="safe")
yaml.default_flow_style = False

build_context = Path(__file__).resolve().parent.parent

with as_file(
    files("dandi") / "tests" / "data" / "dandiarchive-docker" / "docker-compose.yml"
) as path:
    with path.open() as fp:
        compose = yaml.load(fp)
    del compose["services"]["redirector"]["image"]
    compose["services"]["redirector"]["build"] = str(build_context)
    with path.open("w") as fp:
        yaml.dump(compose, fp)
