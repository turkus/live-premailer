# -*- coding: utf-8 -*-
import mock
import os

import pytest

from lpremailer import RenderHandler, JsonGenerator


def random_word():
    return 'dummy'


@mock.patch('lpremailer.utils.rw.random_word', side_effect=random_word)
def test_to_json(self, *args):
    cmd_args = pytest.CmdArgs(loadhistory=False, devpostfix='_dev',
                              livepostfix='_live', astext=False)
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
