import os
import json
import requests


def segment_document(path: str):
    file = dict()
    with open(path, "rb") as f:
        file["file"] = f.read()
    data = {
        "fast": "true",
        # "fast": "false",
    }
    r = requests.post(
        "http://localhost:5060",
        data=data,
        files=file,
    )
    return json.loads(r.content)