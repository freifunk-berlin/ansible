#!/bin/env python3
import json
import urllib.request

with urllib.request.urlopen("https://hopglass.berlin.freifunk.net/meshviewer.json") as url:
    data = json.loads(url.read().decode())

    simplenodelist = list()

    nodes = data.get("nodes")
    for node in nodes:
        simplenode = {
            "latitude": node["location"]["latitude"],
            "longitude": node["location"]["longitude"],
            "name": node["hostname"],
            "key": node["hostname"],
        }
        simplenodelist.append(simplenode.copy())

    print(json.dumps(simplenodelist, separators=(",", ":")))
