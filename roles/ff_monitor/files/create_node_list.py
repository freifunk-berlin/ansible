#!/bin/env python3
import json
import urllib.request

with urllib.request.urlopen("https://hopglass.berlin.freifunk.net/nodes.json") as url:
    data = json.loads(url.read().decode())

    simplenodelist = list()

    nodes = data.get("nodes")
    for node in nodes:
        simplenode = {
            "latitude": node["nodeinfo"]["location"]["latitude"],
            "longitude": node["nodeinfo"]["location"]["longitude"],
            "name": node["nodeinfo"]["hostname"],
            "key": node["nodeinfo"]["hostname"],
        }
        simplenodelist.append(simplenode.copy())

    print(json.dumps(simplenodelist, separators=(",", ":")))
