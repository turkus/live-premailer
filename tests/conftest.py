import collections


def pytest_namespace():
    args = ['loadhistory', 'devpostfix', 'livepostfix', 'astext']
    return {
        'CmdArgs': collections.namedtuple('CmdArgs', args),
    }
