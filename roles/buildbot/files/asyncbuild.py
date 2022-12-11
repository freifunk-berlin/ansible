# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util, steps
from buildbot.process import build, buildstep, factory, logobserver
from twisted.internet import defer
from twisted.python import log

# AsyncBuildGenerator dynamically generates build steps from command output.
#
# It runs stepFunc for every line of stdout from specified command.
# Apart from that it behaves just like a ShellCommand.
#
# see https://docs.buildbot.net/3.6.0/manual/configuration/buildfactories.html
class AsyncBuildGenerator(buildstep.ShellMixin, steps.BuildStep):
    def __init__(self, stepFunc, **kwargs):
        kwargs = self.setupShellMixin(kwargs)
        super().__init__(**kwargs)
        self.observer = logobserver.BufferLogObserver()
        self.addLogObserver('stdio', self.observer)
        self.stepFunc = stepFunc

    def getLines(self, stdout):
        archs = []
        for line in stdout.split('\n'):
            arch = str(line.strip())
            if arch and not arch.startswith('#'):
                archs.append(arch)
        return archs

    @defer.inlineCallbacks
    def run(self):
        cmd = yield self.makeRemoteShellCommand()
        yield self.runCommand(cmd)
        result = cmd.results()
        if result == util.SUCCESS:
            self.build.addStepsAfterCurrentStep([
                self.stepFunc(a) for a in self.getLines(self.observer.getStdout())
            ])
        return result

# AsyncTrigger is a Trigger step which executes in parallel with other AsyncTriggers.
# It's a useful middleground between waitForFinish=False and waitForFinish=True.
#
# Adapted from @vit9696's code at https://github.com/buildbot/buildbot/issues/3088
class AsyncTrigger(steps.Trigger):
    def setAsyncLock(self, lock):
        self.asyncLock = lock

    @defer.inlineCallbacks
    def _createStep(self):
        """
        We need to generate step number with locks as this code
        may now run in parallel.
        """
        self.name = yield self.build.render(self.name)
        self.build.setUniqueStepName(self)
        self.stepid, self.number, self.name = yield self.master.data.updates.addStep(
            buildid=self.build.buildid,
            name=self.name)

    @defer.inlineCallbacks
    def addStep(self):
        """
        Create and start the step, noting that the name may be altered to
        ensure uniqueness.
        """
        yield self.asyncLock.run(self._createStep)
        yield self.master.data.updates.startStep(self.stepid)

    @defer.inlineCallbacks
    def run(self):
        val = self.getProperty("asyncTotal", 0)
        self.setProperty("asyncTotal", val + 1, "AsyncTrigger")

        results = yield super().run()

        if results == util.SUCCESS:
            val = self.getProperty("asyncSuccess", 0)
            self.setProperty("asyncSuccess", val + 1, "AsyncTrigger")
        else:
            val = self.getProperty("asyncUnknown", 0)
            self.setProperty("asyncUnknown", val + 1, "AsyncTrigger")

        return results

# AsyncBuild is a Build which can execute AsyncTrigger steps in parallel.
# It's a useful middleground between waitForFinish=False and waitForFinish=True.
#
# Adapted from @vit9696's code at https://github.com/buildbot/buildbot/issues/3088
class AsyncBuild(build.Build):
    def setupBuild(self):
        """
        Remember async locks and create an async lock itself,
        providing it to the async triggers.
        """
        super().setupBuild()

        self.asyncLock = defer.DeferredLock()

        self.asyncSteps = []
        for step in self.steps:
            if isinstance(step, AsyncTrigger):
                self.asyncSteps.append(step)
                step.setAsyncLock(self.asyncLock)

    def addStepsAfterCurrentStep(self, steps):
        super().addStepsAfterCurrentStep(steps)
        for step in self.steps:
            if isinstance(step, AsyncTrigger):
                self.asyncSteps.append(step)
                step.setAsyncLock(self.asyncLock)

    def stopBuild(self, reason="<no reason given>", results=util.CANCELLED):
        """
        Interrupt not just the current step but also all async steps.
        """
        log.msg(f" {self}: stopping my build: {reason} {results}")
        if self.finished:
            return

        self.stopped = True

        for step in self.asyncSteps:
            step.interrupt(reason)

        return super().stopBuild(reason, results)

    def startNextStep(self):
        """
        Start more than one step when there are async steps in the build.
        """
        while True:
            try:
                s = self.getNextStep()
            except StopIteration:
                s = None
            if s:
                self.executedSteps.append(s)
                self.currentStep = s

                # Run all async steps we have right now.
                if isinstance(s, AsyncTrigger):
                    self._start_next_step_impl(s)
                    continue

                # Start the next non-async step.
                self._start_next_step_impl(s)
                return defer.succeed(None)

            if self.asyncSteps:
                return defer.succeed(None)

            return self.allStepsDone()

    def stepDone(self, results, step):
        """
        Remove step from asyncSteps to ensure last async step
        triggers allStepsDone().
        """
        if isinstance(step, AsyncTrigger):
            self.asyncSteps.remove(step)

        return super().stepDone(results, step)
