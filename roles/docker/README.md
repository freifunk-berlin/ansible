Docker
======

Simple role to deploy a docker-compose file.

It will deploy the file to  `/etc/freifunk/docker-compose.yml` and run a `docker-compose up` on it

If you need extra files for e.g. the containers, make sure to add them beforehand.

Configuration:
--------------

```
docker:
  file: the docker-compose file from the templates directory. Mandatory!
  enable_service: a list of services that should be enabled at the end
  packages: a list of packages to install
  restart_service: a list of services that should be restarted at the end
```
