# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *

from asyncbuild import *

repo = 'https://github.com/pktpls/falter-packages.git'
branches = ['master','openwrt-22.03','openwrt-21.02']

def packagesConfig(c):

  c['change_source'].append(changes.GitPoller(
    repourl=repo,
    workdir='gitpoller-workdir',
    pollInterval=60))

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
          choices=branches,
          default="master",
          strict=True),
        revision=util.FixedParameter(name="revision", default=""),
        repository=util.FixedParameter(name="repository", default=repo),
        project=util.FixedParameter(name="project", default=""))]))

  c['builders'].append(util.BuilderConfig(
    name="builds/packages",
    workernames=["masterworker"],
    factory=packagesFactory(util.BuildFactory())))

  c['builders'].append(util.BuilderConfig(
    name="dummy/packages",
    workernames=["worker1", "worker2", "worker3", "worker4", "worker5", "worker6", "worker7", "worker8"],
    factory=packagesArchFactory(util.BuildFactory()),
    collapseRequests=False))

  return c

# Passed by packagesFactory to AsyncBuildGenerator to be called for each arch.
def archTriggerStep(arch):
  return AsyncTrigger(
    name=util.Interpolate("trigger packages/%(prop:branch)s/%(kw:arch)s", arch=arch),
    waitForFinish=True,
    warnOnFailure=True,
    schedulerNames=["dummy/packages"],
    copy_properties=['repository', 'branch', 'revision', 'got_revision'],
    set_properties={
      'arch': arch,
      'branch': util.Interpolate("%(prop:branch)s"),
      'origbuildnumber': util.Interpolate("%(prop:buildnumber)s"),
      'virtual_builder_name': util.Interpolate("packages/%(prop:branch)s/%(kw:arch)s", arch=arch),
      'virtual_builder_tags': ["packages", util.Interpolate("%(prop:branch)s")]})

# Fans out to one builder per arch and blocks for the results.
def packagesFactory(f):
    f.buildClass = AsyncBuild
    f.addStep(
        steps.Git(
            name="git clone",
            haltOnFailure=True,
            repourl=repo,
            mode='incremental'))
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
| head -n4 \
""")]))

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
    apk add git bash wget xz coreutils build-base gcc abuild binutils ncurses-dev gawk bzip2 perl python3 rsync \
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
    wwwdir = util.Interpolate("public_html/%(kw:wwwpath)s", wwwpath=wwwpath)
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
                "signify -S -m %(kw:wwwdir)s/falter/Packages -s packagefeed_master.sec",
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

    return f
