import json


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    

def save_json(content, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=4, ensure_ascii=False)