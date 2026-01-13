# mirror.berlin.freifunk.net

Host to static mirror Upstream Repos.

We are mirroring:
- downloads.openwrt.org


## Setup

It is a Hardware Box with a Dedicated Storage Drive Mounted at /data

This drive is mounted as noexec



## Services

- Caddy serves everything under `/data/mirror` as static files with dirlisting enabled.
- rsync for specifc directories (e.g. `openwrt` for `/data/mirror/downloads.openwrt.org` )
