#!/bin/sh

print_help() {
    echo "Links a build to the final download-dir."
    echo "Usage:"
    echo '    ./symlink_build.sh $falterversion $buildnumber [-p|-t]'
    echo " "
    echo "Example:"
    echo "    ./symlink_build.sh 1.2.3-snapshot 18 -t"
    echo ""
}

if [ "$1" = "-h" ]; then
    print_help
    exit 1
fi

if [ $# -lt 3 ]; then
    echo "Please give -t or -p ro signalise, if you want to link packages or firmware-images."
    echo ""
    print_help
    exit 1
fi

VERSION="$1"
BUILDNO="$2"
T_OR_P="$3"

if [ ${#VERSION} -lt 5 ]; then
    echo "please give the falter-version first!"
    echo ""
    print_help
    exit 1
fi

if [ "$T_OR_P" = "-t" ]; then
    SYMLINK_SRC="/usr/local/src/www/htdocs/buildbot/unstable/$VERSION"

    rm -vrf "$SYMLINK_SRC"
    ln -s -T "/usr/local/src/www/htdocs/buildbot/builds/targets/$BUILDNO" "$SYMLINK_SRC"

elif [ "$T_OR_P" = "-p" ]; then
    SYMLINK_SRC="/usr/local/src/www/htdocs/buildbot/feed/$VERSION/packages"

    rm -vrf "$SYMLINK_SRC"
    ln -s -T "/usr/local/src/www/htdocs/buildbot/builds/packages/$BUILDNO" "$SYMLINK_SRC"

else
    echo "unrecognized option $T_OR_P !"
    exit 1
fi

echo ""
echo "looks like it worked..."
echo ""
ls -lisah "$SYMLINK_SRC"
