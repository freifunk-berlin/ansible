# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import *

from asyncbuild import *

from config import workerNames, builter_repo, builter_branches


def targetsConfig(c):

  c['change_source'].append(changes.GitPoller(
    repourl=builter_repo,
    workdir='gitpoller-workdir',
    pollInterval=60))

  c['schedulers'].append(schedulers.Triggerable(
    name="dummy/targets",
    builderNames=["dummy/targets"]))

  c['schedulers'].append(schedulers.ForceScheduler(
    name="force-targets",
    builderNames=["builds/targets"],
    codebases=[
      util.CodebaseParameter(
        "",
        label="falter-builter repository",
        branch=util.StringParameter(
          name="branch",
          label="branch",
          default="master"),
        revision=util.FixedParameter(name="revision", default=""),
        repository=util.FixedParameter(name="repository", default=builter_repo),
        project=util.FixedParameter(name="project", default=""))],
    properties=[
        util.StringParameter(
            name="release",
            label="falter release branch",
            default="snapshot")],
    reason=util.FixedParameter(name="reason", default="manual", hide=True)))

  c['builders'].append(util.BuilderConfig(
    name="builds/targets",
    workernames=["masterworker"],
    factory=targetsFactory(util.BuildFactory())))

  c['builders'].append(util.BuilderConfig(
    name="dummy/targets",
    workernames=workerNames,
    factory=targetsTargetFactory(util.BuildFactory()),
    collapseRequests=False))

  return c

# Passed by targetsFactory to AsyncBuildGenerator to be called for each arch.
def targetTriggerStep(target):
  return AsyncTrigger(
    # here is the possiblibilty of running into a nasty bug. Apparently, names
    # for virt-builders shouldn't get too long. otherwise they might not get spawned
    # https://github.com/buildbot/buildbot/issues/3413
    name=util.Interpolate("trigger t/%(prop:branch)s/%(kw:target)s", target=target),
    waitForFinish=True,
    warnOnFailure=True,
    schedulerNames=["dummy/targets"],
    copy_properties=['repository', 'branch', 'revision', 'got_revision', 'release'],
    set_properties={
      'target': target,
      'branch': util.Interpolate("%(prop:branch)s"),
      'origbuildnumber': util.Interpolate("%(prop:buildnumber)s"),
      'virtual_builder_name': util.Interpolate("t/%(prop:branch)s/%(kw:target)s", target=target),
      'virtual_builder_tags': ["targets", util.Interpolate("%(prop:branch)s")]})

# Fans out to one builder per target and blocks for the results.
def targetsFactory(f):
    f.buildClass = AsyncBuild
    f.addStep(
        steps.Git(
            name="git clone",
            haltOnFailure=True,
            repourl=builter_repo,
            mode='incremental'))
    f.addStep(
        AsyncBuildGenerator(targetTriggerStep,
            name="generate builds",
            haltOnFailure=True,
            command=["sh", "-c", util.Interpolate(
                # Read our list of targets to build.
                #
                # 1. Print the architectures-to-targets mapping
                # 2. Remove comments and empty lines
                # 3. Take everything but the first line
                # 4. Print all entries into $targets one by one
                # 5. Go through $targets, print only targets that aren't broken
                #
                # TODO: doesn't fail if targets-*.txt doesn't exist
                '''\
targets=$(\
    cat targets-%(prop:release)s.txt \
    | grep -v "#" | grep . \
    | cut -d" " -f2- \
    | xargs -n1 echo | sort \
) ; \
for t in "$targets"; do \
    if ! cat broken-%(prop:release)s.txt | grep -F "$t" >/dev/null ; \
    then \
        echo "$t" ; \
    fi ; \
done \
''')]))
    f.addStep(
        steps.ShellCommand(
            name=util.Interpolate("%(prop:asyncSuccess)s of %(prop:asyncTotal)s succeeded"),
            command=["true"]))

    return f


@util.renderer
def targetTarFile(props):
  t, st = props['target'].split('/')
  return "targets-{0}-{1}_{2}.tar".format(props['origbuildnumber'], t, st)

def targetsTargetFactory(f):
    f.addStep(
        steps.ShellCommand(
            name="build",
            haltOnFailure=True,
            interruptSignal='TERM', # podman can't proxy the default KILL signal
            command=["sh", "-c", util.Interpolate(
                # Container that prints a tarball to stdout, and other output to stderr.
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
podman run -i --rm --timeout=21600 --log-driver=none docker.io/library/alpine:edge sh -c '\
( \
    apk add git bash wget xz coreutils build-base gcc abuild binutils ncurses-dev gawk bzip2 gettext perl python3 rsync sqlite \
    && git clone %(prop:repository)s /root/falter-builter \
    && cd /root/falter-builter/ \
    && git checkout %(prop:got_revision)s \
    && ./build_falter -p all -v %(prop:release)s -t %(prop:target)s \
) >&2 \
&& cd /root/falter-builter/firmwares \
&& tar -c *' > out.tar \
""")]))

    tarfile = targetTarFile
    wwwpath = util.Interpolate("builds/targets/%(prop:origbuildnumber)s/")
    wwwdir = util.Interpolate("/usr/local/src/www/htdocs/buildbot/%(kw:wwwpath)s", wwwpath=wwwpath)
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
