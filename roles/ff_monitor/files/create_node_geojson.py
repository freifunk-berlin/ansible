#!/bin/env python3
import json
import urllib.request

with urllib.request.urlopen("https://hopglass.berlin.freifunk.net/nodes.json") as url:
    data = json.loads(url.read().decode())

    simplenodelist = list()

    nodes = data.get('nodes')
    for node in nodes:
        simplenode = {"type": "Feature"}

        properties = {}
        geometry = {'type': "Point", 'coordinates': [node['nodeinfo']['location']['longitude'],
                                                     node['nodeinfo']['location']['latitude']]}

        properties['name'] = node['nodeinfo']['hostname']
        simplenode['properties'] = properties
        simplenode['geometry'] = geometry

        simplenodelist.append(simplenode.copy())

    geojson = {"type": "FeatureCollection", 'features': simplenodelist}

    print(json.dumps(geojson, separators=(',', ':')))
