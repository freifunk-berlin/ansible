# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *
import re

from asyncbuild import *

from config import workerNames, packages_repo, packages_branches


def packagesConfig(c):

  c['schedulers'].append(schedulers.Triggerable(
    name="dummy/packages",
    builderNames=["dummy/packages"]))

  c['schedulers'].append(schedulers.ForceScheduler(
    name="force-packages",
    builderNames=["builds/packages"],
    codebases=[
      util.CodebaseParameter(
        "",
        branch=util.ChoiceStringParameter(
          name="branch",
          choices=packages_branches,
          default="master",
          strict=True),
        revision=util.FixedParameter(name="revision", default=""),
        repository=util.FixedParameter(name="repository", default=packages_repo),
        project=util.FixedParameter(name="project", default=""))]))

  c['builders'].append(util.BuilderConfig(
    name="builds/packages",
    workernames=["masterworker"],
    factory=packagesFactory(util.BuildFactory())))

  c['builders'].append(util.BuilderConfig(
    name="dummy/packages",
    workernames=workerNames,
    factory=packagesArchFactory(util.BuildFactory()),
    collapseRequests=False))

  return c

# Passed by packagesFactory to AsyncBuildGenerator to be called for each arch.
def archTriggerStep(arch):
  return AsyncTrigger(
    # here is the possiblibilty of running into a nasty bug. Apparently, names
    # for virt-builders shouldn't get too long. otherwise they might not get spawned
    # https://github.com/buildbot/buildbot/issues/3413
    name=util.Interpolate("trigger p/%(prop:branch)s/%(kw:arch)s", arch=arch),
    waitForFinish=True,
    warnOnFailure=True,
    schedulerNames=["dummy/packages"],
    copy_properties=['repository', 'branch', 'revision', 'got_revision'],
    set_properties={
      'arch': arch,
      'branch': util.Interpolate("%(prop:branch)s"),
      'origbuildnumber': util.Interpolate("%(prop:buildnumber)s"),
      'virtual_builder_name': util.Interpolate("p/%(prop:branch)s/%(kw:arch)s", arch=arch),
      'virtual_builder_tags': ["packages", util.Interpolate("%(prop:branch)s")],
      'falterVersion': util.Interpolate("%(prop:falterVersion)s")
      })


def extract_falter_version(rc, stdout, stderr):
    """provides some logic and regex magic to get a falter-version from a
    freifunk_release file.
    """
    try:
        versionString = re.search("FREIFUNK_RELEASE=['\"](.*)['\"]", stdout)
        falterVersion = versionString.group(1)
    except:
        falterVersion = 'unknown'

    return {'falterVersion': falterVersion}

# Fans out to one builder per arch and blocks for the results.
def packagesFactory(f):
    f.buildClass = AsyncBuild
    f.addStep(
        steps.Git(
            name="git clone",
            haltOnFailure=True,
            repourl=packages_repo,
            # if using incremental, we get strange behaviors, when configuring
            # another repo, that is back the other repo. Doing full checkouts is cleaner
            method='clobber',
            mode='full'))
    f.addStep(
        steps.SetPropertyFromCommand(
            # fetch upload-dir from FREIFUNK_RELEASE variable in freifunk_release file.
            # this file shows the falter-version the feed is intended for
            name="fetch falter feed-version",
            haltOnFailure=True,
            command=["cat",
                util.Interpolate("%(prop:builddir)s/build/packages/falter-common/files-common/etc/freifunk_release")],
            extract_fn=extract_falter_version))
    f.addStep(
        AsyncBuildGenerator(archTriggerStep,
            name="generate builds",
            haltOnFailure=True,
            command=["sh", "-c", util.Interpolate(
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
""")]))
    f.addStep(
        steps.ShellCommand(
            name=util.Interpolate("%(prop:asyncSuccess)s of %(prop:asyncTotal)s succeeded"),
            command=["true"]))

    return f

# Runs build.sh with prop:arch and prop:branch, and uploads the result to master.
def packagesArchFactory(f):
    f.addStep(
        steps.ShellCommand(
            name="build",
            haltOnFailure=True,
            interruptSignal='TERM', # podman can't proxy the KILL signal
            command=["sh", "-c", util.Interpolate(
                # Container that prints a tarball to stdout, and build output to stderr.
                #
                # Parameters:
                # * -i so we get output
                # * no -t because it messes with stdout/stderr
                # * --rm so we don't fill up the disk with old containers
                # * --timeout so we don't accumulate hanging containers
                #   * requires Podman >= 3.2.0
                # * --log-driver so we don't pump huge tarballs into the logging facility
                #   * it'd also trigger a segfault in ~15% of concurrent runs:
                #     https://github.com/containers/podman/issues/13779
                #
                """\
podman run -i --rm --timeout=1800 --log-driver=none docker.io/library/alpine:edge sh -c '\
( \
    apk add git bash wget xz coreutils build-base gcc abuild binutils ncurses-dev gawk bzip2 perl python3 rsync argp-standalone musl-fts-dev musl-obstack-dev musl-libintl \
    && git clone %(prop:repository)s /root/falter-packages \
    && cd /root/falter-packages/ \
    && git checkout %(prop:got_revision)s \
    && build/build.sh %(prop:branch)s %(prop:arch)s out/ \
) >&2 \
&& cd /root/falter-packages/out/ \
&& tar -c *' > out.tar \
""")]))

    tarfile = util.Interpolate("packages-%(prop:origbuildnumber)s-%(prop:arch)s.tar")
    wwwpath = util.Interpolate("builds/packages/%(prop:origbuildnumber)s/%(prop:arch)s")
    wwwdir = util.Interpolate("/usr/local/src/www/htdocs/buildbot/%(kw:wwwpath)s", wwwpath=wwwpath)
    symlinksrc = util.Interpolate("/usr/local/src/www/htdocs/buildbot/feed/%(prop:falterVersion)s/packages/")
    symlinkdest = util.Interpolate("/usr/local/src/www/htdocs/buildbot/builds/packages/%(prop:origbuildnumber)s/*")
    wwwurl = util.Interpolate("https://firmware.berlin.freifunk.net/%(kw:wwwpath)s", wwwpath=wwwpath)
    f.addStep(
        steps.FileUpload(
            name="upload",
            haltOnFailure=True,
            workersrc="out.tar",
            masterdest=tarfile,
            url=wwwurl,
            urlText=wwwurl))
    f.addStep(
        steps.MasterShellCommand(
            name="extract",
            haltOnFailure=True,
            command=["sh", "-c", util.Interpolate(
                "mkdir -vp %(kw:wwwdir)s && tar -v -C %(kw:wwwdir)s -xf %(kw:tarfile)s",
                tarfile=tarfile, wwwdir=wwwdir)]))
    f.addStep(
        steps.MasterShellCommand(
            name="sign",
            haltOnFailure=True,
            command=["sh", "-c", util.Interpolate(
                "signify-openbsd -S -m %(kw:wwwdir)s/falter/Packages -s packagefeed_master.sec",
                wwwdir=wwwdir)]))
    f.addStep(
        steps.MasterShellCommand(
            name="cleanup master",
            alwaysRun=True,
            warnOnFailure=False,
            command=["sh", "-c", util.Interpolate(
                "rm -vf %(kw:tarfile)s",
                tarfile=tarfile)]))
    f.addStep(
        steps.ShellCommand(
            name="cleanup worker",
            alwaysRun=True,
            warnOnFailure=False,
            command=["sh", "-c", "rm -vf out.tar"]))
    # TODO: Make the following 3 steps better by having one symlink as the
    # packages dir, not multiple within the packages dir.
    # f.addStep(
    #     steps.MasterShellCommand(
    #         name="remove symlinks to old artifacts",
    #         haltOnFailure=True,
    #         command=["sh", "-c", util.Interpolate(
    #             "rm -vrf %(kw:symlinksrc)s", symlinksrc=symlinksrc)]))
    # f.addStep(
    #     steps.MasterShellCommand(
    #         name="recreate directory for symlinks",
    #         haltOnFailure=True,
    #         command=["sh", "-c", util.Interpolate(
    #             "mkdir -p %(kw:symlinksrc)s", symlinksrc=symlinksrc)]))
    # f.addStep(
    #     steps.MasterShellCommand(
    #         name="symlink artifacts to url",
    #         # might have happened, that another worker created the links already.
    #         # That isn't a problem though
    #         haltOnFailure=False,
    #         command=["sh", "-c", util.Interpolate(
    #             "ln -s %(kw:symlinkdest)s %(kw:symlinksrc)s", symlinkdest=symlinkdest, symlinksrc=symlinksrc)]))

    return f
