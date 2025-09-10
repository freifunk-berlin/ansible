Aktuelle MediaWiki-Installation
===============================

/opt/wiki.freifunk.net# ls
wwwroot/                       - MediaWiki-Installation
static/                        - statische Dateien, Bilder

Eigentlich war Ziel, in mediawiki/ ausschließlich ein unmodifiziertes MediaWiki
zu haben; das Freifunk-Skin und Semantic MediaWiki/Semantic Maps mussten aber
doch mit rein. Bilder und weitere Extensions werden per Apache-Config bzw. Symlinks
eingebunden.


Installation
============

Siehe tasks/main.yml


Update
======

systemctl stop cron
systemctl stop caddy

mv /opt/wiki.freifunk.net/wwwroot  /opt/wiki.freifunk.net/wwwroot_old
wget -O /tmp/mediawiki.tar.gz https://releases.wikimedia.org/mediawiki/1.43/mediawiki-1.43.3.tar.gz
tar xf /tmp/mediawiki.tar.gz -C /opt/wiki.freifunk.net/wwwroot --strip-components=1
chown -R caddy:caddy /opt/wiki.freifunk.net/wwwroot


> ansible laufen lassen (extensions etc)
sudo -u caddy php /opt/wiki.freifunk.net/wwwroot/maintenance/run.php update.php
sudo -u caddy php /opt/wiki.freifunk.net/wwwroot/maintenance/run.php SemanticMediaWiki:rebuildData.php -v --with-maintenance-log

> Rendert jede seite
sudo -u caddy php /opt/wiki.freifunk.net/wwwroot/maintenance/run.php rebuildFileCache.php --all



Checkliste
==========

* Logo fehlt? skins/common aus alter Installation kopieren.
* SMW-Attribute sagen "Verarbeitungsfehler"? rebuildData nochmal laufenlassen (s.o.).
* https://wiki.freifunk.net/extensions/OWM/osmcenter.php?latlon=52.514169,13.433311
* https://wiki.freifunk.net/Medienspiegel (RSS)
