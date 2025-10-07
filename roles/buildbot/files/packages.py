# -*- python -*-
# ex: set filetype=python:

from asyncbuild import *
from buildbot.plugins import *

# shut up, flake8 and learn to deal with bulk imports instead of loading everthing
# explicitly! We don't bother for lines longer than 80 chars too. We don't use
# punchcards anymore!
# flake8: noqa: F403, F405, E501

# linter should not bother us with variable "schedulers" not defined. It it
# defined indeed and is an imported object
# pylint: disable=E0602


def packagesConfig(c, config):
    c["schedulers"].append(
        schedulers.Triggerable(name="dummy/packages", builderNames=["dummy/packages"])
    )

    c["schedulers"].append(
        schedulers.ForceScheduler(
            name="force-packages",
            buttonName="Build Package Feed",
            builderNames=["builds/packages"],
            codebases=[
                util.CodebaseParameter(
                    "",
                    label="Build falter package feeds using falter-packages.git",
                    branch=util.ChoiceStringParameter(
                        name="branch",
                        label="git branch",
                        choices=config["packages_branches"],
                        default=config["packages_branches"][0],
                        strict=True,
                    ),
                    revision=util.FixedParameter(name="revision", default=""),
                    repository=util.FixedParameter(
                        name="repository", default=config["packages_repo"]
                    ),
                    project=util.FixedParameter(name="project", default=""),
                )
            ],
        )
    )

    c["builders"].append(
        util.BuilderConfig(
            name="builds/packages",
            workernames=["masterworker"],
            factory=packagesFactory(util.BuildFactory(), config["publishDir"]),
            collapseRequests=False,
            tags=["toplevel"],
        )
    )

    c["builders"].append(
        util.BuilderConfig(
            name="dummy/packages",
            workernames=config["workerNames"],
            factory=packagesArchFactory(
                util.BuildFactory(),
                config["publishDir"],
                config["publishURL"],
                config["alpineVersion"],
            ),
            collapseRequests=False,
        )
    )

    return c


# Passed by packagesFactory to AsyncBuildGenerator to be called for each arch.
def archTriggerStep(arch):
    return AsyncTrigger(
        # Step name limit is 50 chars, longest is currently 33 chars:
        # "trigger arm_cortex-a15_neon-vfpv4"
        # See https://github.com/buildbot/buildbot/issues/3413
        name=util.Interpolate("trigger %(kw:arch)s", arch=arch),
        waitForFinish=True,
        warnOnFailure=True,
        schedulerNames=["dummy/packages"],
        copy_properties=["repository", "branch", "revision", "got_revision"],
        set_properties={
            "arch": arch,
            "origbuildnumber": util.Interpolate("%(prop:buildnumber)s"),
            # Builder name limit is 70 characters, longest is currently 48 chars:
            # packages/openwrt-22.03/arm_cortex-a15_neon-vfpv4
            # See https://github.com/buildbot/buildbot/pull/3957
            "virtual_builder_name": util.Interpolate(
                "packages/%(prop:branch)s/%(kw:arch)s", arch=arch
            ),
            "virtual_builder_tags": [],
        },
    )


# Only needed for publishing, see pubdir further below.
# Apart from that only used for targets builds.
@util.renderer
def branchToFalterBranch(props):
    o2f = {
        "main": "snapshot",
        "openwrt-24.10": "1.5.0-snapshot",
        "openwrt-23.05": "1.4.0-snapshot",
        "openwrt-22.03": "1.3.0-snapshot",
        "openwrt-21.02": "1.2.3-snapshot",
        "testbuildbot": "testbuildbot",
    }
    return o2f.get(props["branch"])


@util.renderer
def signCommand(props, wwwdir):
    match props["branch"]:
        case "openwrt-24.10" | "openwrt-23.05" | "openwrt-22.03" | "openwrt-21.02":
            return f"signify-openbsd -S -m {wwwdir}/falter/Packages -s packagefeed_master.sec"
        case _:
            return f"apk adbsign --allow-untrusted --sign-key apk.snapshot.PRIVATE.pem {wwwdir}/falter/packages.adb"


# Fans out to one builder per arch and blocks for the results.
def packagesFactory(f, wwwPrefix):
    f.buildClass = AsyncBuild
    f.addStep(
        steps.SetProperty(
            name=util.Interpolate("falterBranch = %(kw:fv)s", fv=branchToFalterBranch),
            property="falterBranch",
            value=branchToFalterBranch,
        )
    )
    f.addStep(
        steps.Git(
            name="git clone",
            haltOnFailure=True,
            repourl=util.Interpolate("%(prop:repository)s"),
            # if using incremental, we get strange behaviors, when configuring
            # another repo, that is back the other repo. Doing full checkouts is cleaner
            method="clobber",
            mode="full",
            submodules=True,
        )
    )
    f.addStep(
        AsyncBuildGenerator(
            archTriggerStep,
            name="generate builds",
            haltOnFailure=True,
            command=[
                "sh",
                "-c",
                util.Interpolate(
                    # Read our list of package architectures to build:
                    #
                    # 1. Print the architectures-to-targets mapping
                    # 2. Remove comments and empty lines
                    # 3. Take only the first column (delimited by a space)
                    #
                    # TODO: doesn't fail if targets-*.txt doesn't exist
                    """\
cat build/targets-%(prop:branch)s.txt \
| grep -v '#' | grep . \
| cut -d' ' -f1 \
"""
                ),
            ],
        )
    )

    wwwdir = util.Interpolate(
        "%(kw:prefix)s/builds/packages/%(prop:buildnumber)s", prefix=wwwPrefix
    )
    pubdir = util.Interpolate(
        "%(kw:prefix)s/feed/%(prop:falterBranch)s/packages", prefix=wwwPrefix
    )
    f.addStep(
        steps.MasterShellCommand(
            name="publish",
            haltOnFailure=True,
            command=[
                "sh",
                "-c",
                util.Interpolate(
                    # Publish build in a way that minimizes downtime.
                    #
                    # We call the currently published artifacts "current",
                    # which is e.g. /unstable/1.3.0-snapshot or /unstable/snapshot.
                    # We also use two temporary directories called "new" and "prev".
                    #
                    # 1. Remove "new" and "prev" leftovers from previous builds
                    # 2. Move build artifacts into "new"
                    # 3. Rename "current" published stuff to "prev"
                    # 4. Publish "new" by renaming it to "current"
                    # 5. Remove "prev"
                    #
                    # This is slightly different from targets builds,
                    # where we only move instead of copy+move.
                    # That means /builds/packages/%d is available after publishing,
                    # while it's empty for targets builds.
                    #
                    # Packages downloads are only unavailable after step 3 and
                    # before step 4 has completed.
                    #
                    # Just symlinking from /builds/packages/%d is not a good option,
                    # since we want to be able to just delete that at any time,
                    # without worrying about symlinks pointing to deleted stuff.
                    """\
mkdir -p %(kw:p)s %(kw:p)s.new \
    && cp -a %(kw:w)s/* %(kw:p)s.new/ \
    && mv %(kw:p)s %(kw:p)s.prev \
    && mv %(kw:p)s.new %(kw:p)s \
    && rm -rf %(kw:w)s %(kw:p)s.prev \
""",
                    w=wwwdir,
                    p=pubdir,
                ),
            ],
        )
    )

    return f


# Runs build.sh with prop:arch and prop:branch, and uploads the result to master.
def packagesArchFactory(f, wwwPrefix, wwwURL, alpineVersion):
    f.addStep(
        steps.ShellCommand(
            name="build",
            haltOnFailure=True,
            interruptSignal="TERM",  # podman can't proxy the KILL signal
            command=[
                "sh",
                "-c",
                util.Interpolate(
                    # Container that prints a tarball to stdout, and build output to stderr.
                    #
                    # Parameters:
                    # * -i so we get output
                    # * no -t because it messes with stdout/stderr
                    # * --rm so we don't fill up the disk with old containers
                    # * --log-driver so we don't pump huge tarballs into the logging facility
                    #   * it'd also trigger a segfault in ~15% of concurrent runs:
                    #     https://github.com/containers/podman/issues/13779
                    #
                    """\
sudo podman run -i --rm --log-driver=none --network=slirp4netns --tmpfs /root:rw,size=12582912k,mode=1777 docker.io/library/alpine:%(kw:alpineVersion)s sh -c '\
( \
    apk add git bash wget zstd xz gzip unzip grep diffutils findutils coreutils build-base gcc abuild binutils ncurses-dev gawk bzip2 perl python3 rsync argp-standalone musl-fts-dev musl-obstack-dev musl-libintl py3-setuptools \
    && git clone %(prop:repository)s /root/falter-packages \
    && cd /root/falter-packages/ \
    && git checkout %(prop:got_revision)s \
    && git submodule init \
    && git submodule update \
    && env FALTER_MIRROR=https://mirror.freifunk.dev build/build.sh %(prop:branch)s %(prop:arch)s out/ \
    && rm -vf out/%(prop:branch)s/%(prop:arch)s/public-key.pem \
) >&2 \
&& cd /root/falter-packages/out/ \
&& tar -c *' > out.tar \
""",
                    alpineVersion=alpineVersion,
                ),
            ],
        )
    )

    tarfile = util.Interpolate("packages-%(prop:origbuildnumber)s-%(prop:arch)s.tar")
    wwwpath = util.Interpolate("builds/packages/%(prop:origbuildnumber)s/%(prop:arch)s")
    wwwdir = util.Interpolate(
        "%(kw:prefix)s/%(kw:wwwpath)s", prefix=wwwPrefix, wwwpath=wwwpath
    )
    f.addStep(
        steps.FileUpload(
            name="upload",
            haltOnFailure=True,
            workersrc="out.tar",
            masterdest=tarfile,
        )
    )
    f.addStep(
        steps.MasterShellCommand(
            name="extract",
            haltOnFailure=True,
            command=[
                "sh",
                "-c",
                util.Interpolate(
                    "mkdir -vp %(kw:wwwdir)s && tar -v -C %(kw:wwwdir)s -xf %(kw:tarfile)s",
                    tarfile=tarfile,
                    wwwdir=wwwdir,
                ),
            ],
        )
    )
    f.addStep(
        steps.MasterShellCommand(
            name="sign",
            haltOnFailure=True,
            command=["sh", "-c", signCommand.withArgs(wwwdir)],
        )
    )
    f.addStep(
        steps.MasterShellCommand(
            name="cleanup master",
            alwaysRun=True,
            warnOnFailure=False,
            command=[
                "sh",
                "-c",
                util.Interpolate("rm -vf %(kw:tarfile)s", tarfile=tarfile),
            ],
        )
    )
    f.addStep(
        steps.ShellCommand(
            name="cleanup worker",
            alwaysRun=True,
            warnOnFailure=False,
            command=["sh", "-c", "rm -vf out.tar"],
        )
    )

    return f
