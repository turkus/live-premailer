import collections
import pytest


def args_fixture():
    args = ['loadhistory', 'devpostfix', 'livepostfix', 'astext']
    return collections.namedtuple('CmdArgs', args)


def pytest_configure():
    pytest.CmdArgs = args_fixture()
