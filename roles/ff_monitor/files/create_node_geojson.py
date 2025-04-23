#!/bin/env python3
import json
import urllib.request
import requests


PROMETHEUS_HOST="localhost:9090"



dhcp_leases=requests.get('http://localhost:9090/api/v1/query', params={'query': 'collectd_dhcpleases_count{}'})


LEASES_DICT = dict()



for node in dhcp_leases.json()['data']['result']:
    node_name = node['metric']['exported_instance']
    leases = node['value'][1]
    LEASES_DICT[node_name] = leases



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
        properties['leases'] = LEASES_DICT.get(node['nodeinfo']['hostname'], 0)

        simplenode['properties'] = properties
        simplenode['geometry'] = geometry

        simplenodelist.append(simplenode.copy())

    geojson = {"type": "FeatureCollection", 'features': simplenodelist}

    print(json.dumps(geojson, separators=(',', ':')))
