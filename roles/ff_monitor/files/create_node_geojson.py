#!/bin/env python3
import json
import urllib.request
import requests

PROMETHEUS_HOST="localhost:8428"

dhcp_leases=requests.get(f'http://{PROMETHEUS_HOST}/api/v1/query', params={'query': 'collectd_dhcpleases_count{}'}, timeout=30)

LEASES_DICT = dict()

for node in dhcp_leases.json()['data']['result']:
    node_name = node['metric']['exported_instance']
    leases = node['value'][1]
    LEASES_DICT[node_name] = leases


with urllib.request.urlopen("https://hopglass.berlin.freifunk.net/meshviewer.json") as url:
    data = json.loads(url.read().decode())

    simplenodelist = list()

    nodes = data.get('nodes')
    for node in nodes:
        simplenode = {"type": "Feature"}

        properties = {}
        geometry = {'type': "Point", 'coordinates': [node['location']['longitude'],
                                                     node['location']['latitude']]}

        properties['name'] = node['hostname']
        properties['leases'] = LEASES_DICT.get(node['hostname'], 0)

        simplenode['properties'] = properties
        simplenode['geometry'] = geometry

        simplenodelist.append(simplenode.copy())

    geojson = {"type": "FeatureCollection", 'features': simplenodelist}

    print(json.dumps(geojson, separators=(',', ':')))
