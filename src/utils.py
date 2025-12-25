# -*- coding: utf-8 -*-

import json

def json_prettify(data):
    return json.dumps(data, indent=4, default=str)

def read_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(file_path, content):
    with open(file_path, "w") as f:
        f.write(content)
