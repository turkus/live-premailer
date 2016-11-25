# -*- coding: utf-8 -*-
import collections
import mock
import os

from lpremailer import RenderHandler, JsonGenerator


CmdArgs = collections.namedtuple('CmdArgs',
                                 ['loadhistory', 'devpostfix', 'livepostfix'])


def random_word():
    return 'dummy'


@mock.patch('lpremailer.utils.rw.random_word', side_effect=random_word)
def test_whatever(self, *args):
    cmd_args = CmdArgs(loadhistory=False, devpostfix='_dev',
                       livepostfix='_live')
    handler = RenderHandler(cmd_args)
    path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(path, 'templates')
    generator = JsonGenerator(handler, path)
    generator.handler.filebase = 'index_dev'
    result = generator.feed()
    expected = {
        'alone_guy': 'dummy',
        'condition': 'dummy',
        'items': [{
            'run': 'lambda x: "dummy"',
            'variable': 'dummy',
            'nothing': {
                'something': {'else': 'dummy'}
            }
        }],
        'data': [{
            'something': {'run': 'lambda x: "dummy"'},
            'variable': 'dummy',
            'nothing': {
                'something': {'else': 'dummy'}
            }
        }],
        'request': {'static_url': 'lambda x: "dummy"'},
    }
    assert result == expected
