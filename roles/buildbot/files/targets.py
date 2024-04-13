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


# jscpd:ignore-start
def targetsConfig(c, config):
    c["schedulers"].append(
        schedulers.Triggerable(name="dummy/targets", builderNames=["dummy/targets"])
    )

    c["schedulers"].append(
        schedulers.ForceScheduler(
            name="force-targets",
            label="Snapshot",
            buttonName="Build Snapshot",
            builderNames=["builds/targets"],
            codebases=[
                util.CodebaseParameter(
                    "",
                    label="Build falter snapshot images using falter-builter.git",
                    branch=util.ChoiceStringParameter(
                        name="branch",
                        label="git branch",
                        choices=config["builter_branches"],
                        default=config["builter_branches"][0],
                        strict=True,
                    ),
                    revision=util.FixedParameter(name="revision", default=""),
                    repository=util.FixedParameter(
                        name="repository", default=config["builter_repo"]
                    ),
                    project=util.FixedParameter(name="project", default=""),
                )
            ],
            properties=[
                util.ChoiceStringParameter(
                    name="falterBranch",
                    label="falter release branch",
                    choices=config["builter_releaseBranches"],
                    default=config["builter_releaseBranches"][0],
                    strict=True,
                )
            ],
            reason=util.FixedParameter(name="reason", default="manual", hide=True),
        )
    )

    c["schedulers"].append(
        schedulers.ForceScheduler(
            name="force-release",
            label="Release",
            buttonName="Build Release",
            builderNames=["builds/targets"],
            codebases=[
                util.CodebaseParameter(
                    "",
                    label="Build falter release",
                    branch=util.ChoiceStringParameter(
                        name="branch",
                        label="git branch",
                        choices=config["builter_branches"],
                        default=config["builter_branches"][0],
                        strict=True,
                    ),
                    revision=util.FixedParameter(name="revision", default=""),
                    repository=util.FixedParameter(
                        name="repository", default=config["builter_repo"]
                    ),
                    project=util.FixedParameter(name="project", default=""),
                )
            ],
            properties=[
                util.StringParameter(
                    name="falterVersion",
                    label="falter release version - e.g. 1.2.3 or 1.1.1-rc1",
                )
            ],
            reason=util.FixedParameter(name="reason", default="manual", hide=True),
        )
    )

    c["builders"].append(
        util.BuilderConfig(
            name="builds/targets",
            workernames=["masterworker"],
            factory=targetsFactory(util.BuildFactory(), config["publishDir"]),
            collapseRequests=False,
        )
    )

    c["builders"].append(
        util.BuilderConfig(
            name="dummy/targets",
            workernames=config["workerNames"],
            factory=targetsTargetFactory(
                util.BuildFactory(),
                config["publishDir"],
                config["publishURL"],
                config["alpineVersion"],
            ),
            collapseRequests=False,
        )
    )

    return c


# jscpd:ignore-end


# Passed by targetsFactory to AsyncBuildGenerator to be called for each arch.
def targetTriggerStep(target):
    return AsyncTrigger(
        # Step name limit is 50 chars, longest is currently 26 chars:
        # "trigger lantiq/xway_legacy"
        # See https://github.com/buildbot/buildbot/issues/3413
        name=util.Interpolate("trigger %(kw:target)s", target=target),
        waitForFinish=True,
        warnOnFailure=True,
        schedulerNames=["dummy/targets"],
        copy_properties=[
            "repository",
            "branch",
            "revision",
            "got_revision",
            "falterBranch",
            "falterVersion",
        ],
        set_properties={
            "target": target,
            "origbuildnumber": util.Interpolate("%(prop:buildnumber)s"),
            # Builder name limit is 70 characters, longest is currently 40 chars:
            # targets/openwrt-22.03/lantiq/xway_legacy
            # See https://github.com/buildbot/buildbot/pull/3957
            "virtual_builder_name": util.Interpolate(
                "targets/%(prop:falterBranch)s/%(kw:target)s", target=target
            ),
            "virtual_builder_tags": [
                "targets",
                util.Interpolate("%(prop:falterBranch)s"),
            ],
        },
    )


@util.renderer
def targetsFalterBranch(props):
    fb = props.getProperty("falterBranch", "")
    fv = props.getProperty("falterVersion", "")
    if fb != "":
        return fb
    elif fv.startswith("1.2.3"):
        return "1.2.3-snapshot"
    elif fv.startswith("1.3.0"):
        return "1.3.0-snapshot"
    elif fv.startswith("1.4.0"):
        return "1.4.0-snapshot"
    else:
        return "snapshot"


@util.renderer
def targetsFalterVersion(props):
    return props.getProperty("falterVersion", props.getProperty("falterBranch", ""))


@util.renderer
def targetsPubDir(props):
    fv = props.getProperty("falterVersion", "")
    if "-" in fv or "snapshot" in fv or "testbuildbot" in fv:
        return "unstable/" + fv
    else:
        return "stable/" + fv


# Fans out to one builder per target and blocks for the results.
def targetsFactory(f, wwwPrefix):
    f.buildClass = AsyncBuild
    f.addStep(
        steps.SetProperty(
            name=util.Interpolate("falterBranch = %(kw:fb)s", fb=targetsFalterBranch),
            property="falterBranch",
            value=targetsFalterBranch,
        )
    )
    f.addStep(
        steps.SetProperty(
            name=util.Interpolate("falterVersion = %(kw:fv)s", fv=targetsFalterVersion),
            property="falterVersion",
            value=targetsFalterVersion,
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
            targetTriggerStep,
            name="generate builds",
            haltOnFailure=True,
            command=[
                "sh",
                "-c",
                util.Interpolate(
                    # Read our list of targets to build.
                    #
                    # 1. Print the architectures-to-targets mapping
                    # 2. Remove comments and empty lines
                    # 3. Take everything but the first line
                    # 4. Print all entries into $targets one by one
                    # 5. Go through $targets, print only targets that aren't broken
                    #
                    # TODO: doesn't fail if targets-*.txt doesn't exist
                    """\
targets=$(\
    cat .buildconf/targets-%(prop:falterBranch)s.txt \
    | grep -v "#" | grep . \
    | cut -d" " -f2- \
    | xargs -n1 echo | sort \
) ; \
for t in $targets; do \
    if ! cat .buildconf/broken-%(prop:falterBranch)s.txt | grep -F "$t" >/dev/null ; \
    then \
        echo "$t" ; \
    fi ; \
done \
"""
                ),
            ],
        )
    )

    wwwdir = util.Interpolate(
        "%(kw:prefix)s/builds/targets/%(prop:buildnumber)s", prefix=wwwPrefix
    )
    pubdir = util.Interpolate("%(kw:pr)s/%(kw:pd)s", pr=wwwPrefix, pd=targetsPubDir)
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
                    # This is slightly different from packages builds,
                    # where we copy+move instead of just move.
                    # We just don't have the hardware to copy >50 GB quickly.
                    # That means /builds/targets/%d is empty after publishing,
                    # while it's kept available for packages builds.
                    #
                    # Targets downloads are only unavailable after step 3 and
                    # before step 4 has completed.
                    #
                    # Just symlinking from /builds/targets/%d is not a good option,
                    # since we want to be able to just delete that at any time,
                    # without worrying about symlinks pointing to deleted stuff.
                    """\
mkdir -p %(kw:p)s %(kw:p)s.new \
    && rm -rf %(kw:p)s.new/* %(kw:p)s.prev \
    && mv %(kw:w)s/* %(kw:p)s.new/ \
    && mv %(kw:p)s %(kw:p)s.prev \
    && mv %(kw:p)s.new %(kw:p)s \
    && rm -rf %(kw:p)s.prev \
""",
                    w=wwwdir,
                    p=pubdir,
                ),
            ],
        )
    )

    return f


@util.renderer
def targetsTarFile(props):
    t, st = props["target"].split("/")
    return "targets-{0}-{1}_{2}.tar".format(props["origbuildnumber"], t, st)


def targetsTargetFactory(f, wwwPrefix, wwwURL, alpineVersion):
    f.addStep(
        steps.ShellCommand(
            name="build",
            haltOnFailure=True,
            interruptSignal="TERM",  # podman can't proxy the default KILL signal
            command=[
                "sh",
                "-c",
                util.Interpolate(
                    # Container that prints a tarball to stdout, and other output to stderr.
                    #
                    # Parameters:
                    # * -i so we get output
                    # * no -t because it messes with stdout/stderr
                    # * --rm so we don't fill up the disk with old containers
                    # * --log-driver so we don't pump huge tarballs into the logging facility
                    #   * it'd also trigger a segfault in ~15% of concurrent runs:
                    #     https://github.com/containers/podman/issues/13779
                    #
                    # Originally we'd also set --timeout, but the workers perf is
                    # very inconsistent. Build times regularly went very long,
                    # so long that --timeout didn't make sense anymore.
                    # It was more of a preventive measure anyway,
                    # since hanging builds aren't a problem that we've had so far.
                    # In addition, manual build cancellation is very reliable
                    # and would be an effective countermeasure.
                    #
                    # We tried to speed things up with a ramdisk filesystem,
                    # but this had very little performance impact in production:
                    # --tmpfs /root:rw,size=6291456k,mode=1777
                    # Also larger targets seemed to need more than 6 GiB.
                    #
                    """\
podman run -i --rm --log-driver=none docker.io/library/alpine:%(kw:alpineVersion)s sh -c '\
( \
    apk add git bash wget zstd gzip unzip grep diffutils findutils coreutils build-base gcc abuild binutils ncurses-dev gawk bzip2 gettext perl python3 rsync sqlite flex libxslt \
    && git clone %(prop:repository)s /root/falter-builter \
    && cd /root/falter-builter/ \
    && git checkout %(prop:got_revision)s \
    && git submodule init \
    && git submodule update \
    && ./build_falter -p all -v %(prop:falterVersion)s -t %(prop:target)s \
) >&2 \
&& cd /root/falter-builter/firmwares \
&& tar -c *' > out.tar \
""",
                    alpineVersion=alpineVersion,
                ),
            ],
        )
    )

    tarfile = targetsTarFile
    wwwpath = util.Interpolate("builds/targets/%(prop:origbuildnumber)s/")
    wwwdir = util.Interpolate(
        "%(kw:prefix)s/%(kw:wwwpath)s", prefix=wwwPrefix, wwwpath=wwwpath
    )
    wwwurl = util.Interpolate("%(kw:url)s/%(kw:wwwpath)s", url=wwwURL, wwwpath=wwwpath)
    f.addStep(
        steps.FileUpload(
            name="upload",
            haltOnFailure=True,
            workersrc="out.tar",
            masterdest=tarfile,
            url=wwwurl,
            urlText=wwwurl,
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
