#!/bin/sh

# Somewho it didn't work to execute that command in a buildbot-mastershell
# Thus, we execute it via that script. Probably the shell failed at the special
# wildcard...

# rm -rf /usr/local/src/www/htdocs/buildbot/unstable/1.1.1-snapshot/*/mpc85xx/

# This clears the images of a specific target while leaving the other ones.
# That is useful, when we generate new images for a target

rm -rf $1
