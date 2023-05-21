# -*- python -*-
# ex: set filetype=python:

from buildbot.plugins import util, steps
from buildbot.reporters.base import ReporterBase
from buildbot.reporters.generators.build import BuildStartEndStatusGenerator
from buildbot.reporters.generators.buildrequest import BuildRequestGenerator
from buildbot.reporters.message import MessageFormatterRenderable
from buildbot.util import httpclientservice
from buildbot.process.results import statusToString

from twisted.internet import defer
from twisted.python import log

import pprint

class MatrixNotifier(ReporterBase):

    def __init__(self, homeserver=None, accessToken=None, room=None, **kwargs):
        self.homeserver = homeserver
        self.accessToken = accessToken
        self.room = room
        super().__init__(**kwargs)

    def checkConfig(self, context=None, debug=None, verify=None, generators=None,
                    **kwargs):
        if generators is None:
            generators = self._create_default_generators()

        super().checkConfig(generators=generators, **kwargs)

    @defer.inlineCallbacks
    def reconfigService(self, context=None, debug=None,
                        verify=None, generators=None, **kwargs):
        self.debug = debug
        self.verify = verify
        self.context = self.setup_context(context)
        if generators is None:
            generators = self._create_default_generators()

        yield super().reconfigService(generators=generators, **kwargs)

    def setup_context(self, context):
        return context or util.Interpolate('buildbot/%(prop:buildername)s')

    # This is needed but I have no clue what it does.
    def _create_default_generators(self):
        start_formatter = MessageFormatterRenderable('Build started.')
        end_formatter = MessageFormatterRenderable('Build done.')
        pending_formatter = MessageFormatterRenderable('Build pending.')

        return [
            BuildRequestGenerator(formatter=pending_formatter),
            BuildStartEndStatusGenerator(start_formatter=start_formatter,
                                         end_formatter=end_formatter)
        ]

    @defer.inlineCallbacks
    def sendMessage(self, reports):
        b = reports[0]['builds'][0]
        builder = b['builder']['name']

        if 'number' not in b or b['complete'] != True or (builder != 'builds/targets' and builder != 'builds/packages'):
            return

        # pp = pprint.PrettyPrinter(indent=4)
        # log.msg(f'MatrixNotifier.sendMessage - {pp.pformat(reports)}')

        version = b['properties']['branch'][0]
        if builder == 'builds/targets':
            version = b['properties']['falterVersion'][0]

        result = statusToString(b['results'])
        color = '#ff0000'
        if b['results'] == 0:
            color = '#008000'

        url = b['url']

        msg = f'{builder} @ {version} · {result} · {url}'
        htmlmsg = f'{builder} @ {version} · <font color="{color}">{result}</font> · {url}'

        http = yield httpclientservice.HTTPClientService.getService(
            self.master, self.homeserver)

        res = http.post(
            f'/_matrix/client/r0/rooms/{self.room}/send/m.room.message?access_token={self.accessToken}',
            json={'msgtype':'m.notice', 'body':msg,
                'format':'org.matrix.custom.html', 'formatted_body':htmlmsg})

