#!/bin/sh

# This script signs packages in a package-feed

REALPATH_SCRIPT=$(realpath "$0")
KEY=$(dirname "$REALPATH_SCRIPT")
KEY="$KEY""/packagefeed_master.sec"

echo "$KEY"
cd "$1"

echo "$PWD"

PACKAGE_LISTS=$(find -name "Packages")
for LIST in $PACKAGE_LISTS; do
        echo "$LIST"
        signify-openbsd -S -m "$LIST" -s "$KEY"
done
