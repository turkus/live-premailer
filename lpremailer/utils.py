import os
import urllib

import six


HERE = os.getcwd()


def parse_params(params):
    return ' '.join((
        '--{}={}'.format(key, value) if value else '--{}'.format(key)
        for key, value in params.items()))


def unquote(html):
    if six.PY3:
        return urllib.parse.unquote(html)
    return urllib.unquote(html)


def object_hook(obj):
    result = {}
    for key, value in obj.items():
        if isinstance(value, six.string_types) and u'lambda' in value:
            result[key] = eval(value)
        else:
            result[key] = value
    return result


class JsonGenerator():
    def __init__(self, devpostfix):
        self.devpostfix = devpostfix

    def generate(self):
        for filename in os.listdir(HERE):
            filebase, ext = os.path.splitext(filename)
            if filebase.endswith(self.devpostfix):
                self.create_file(filebase)

    def create_file(self, filebase):
        filebase = filebase.replace(self.devpostfix, '')
        filename = '{}{}.json'.format(filebase, self.devpostfix)
        filepath = os.path.join(HERE, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w+') as fjson:
                fjson.write('{}')
