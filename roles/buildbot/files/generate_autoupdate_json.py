#!/usr/bin/python3

# {{ ansible_managed }}

import argparse
import json
import os


parser = argparse.ArgumentParser()
parser.add_argument('-v', dest='version', type=str, required=True,
                    help='falter-version that the autoupdate-file is for.')
parser.add_argument('-p', dest='dir', type=str, required=True,
                    help='version directory, in which there are tunneldigger- and notunnel- dirs. autoupdate.json will be placed in that directory too.')
args = parser.parse_args()

# build autoupdate.json
autoupdate_json = {}
autoupdate_json[
    "image_url"] = "https://firmware.berlin.freifunk.net/stable/{falter-version}/{flavour}/{target}"
autoupdate_json["target"] = {}
autoupdate_json["falter-version"] = args.version

# get paths of all json-files
file_list = os.popen('find ' + args.dir + ' -name "*.json"').read().split()

# aggregate the content of all files
for fpath in file_list:
    # read in file
    fp = open(fpath, "r")
    profiles_json = json.load(fp)
    fp.close()

    # only the profiles are interesting
    profiles = profiles_json.get("profiles")
    # print(profiles)

    # get flavour and omit backbone-images
    flavour = fpath.split('/')[-4]
    if flavour == "backbone":
        continue

    # get target and create dict, if not already created
    target = '/'.join(fpath.split('/')[-3:-1])
    if autoupdate_json.get("target").get(target) == None:
        autoupdate_json["target"][target] = {}

    # get hashsums
    for model in profiles:
        images = profiles.get(model).get("images")
        sha256 = None  # reset hashsum for next iteration
        for i in images:
            if i.get("type") == "sysupgrade":
                sha256 = i.get("sha256")
                break

        # add information to autoupdate.json
        if autoupdate_json.get("target").get(target).get(model) == None:
            autoupdate_json["target"][target][model] = {}

        if sha256 is not None:
            if flavour == "notunnel":
                autoupdate_json["target"][target][model]["notunnel"] = sha256
            else:
                autoupdate_json["target"][target][model]["tunneldigger"] = sha256

# write autoupdate.json to disk
with open(args.dir + "/autoupdate.json", "w") as f:
    f.write(json.dumps(autoupdate_json))
