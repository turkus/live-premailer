import json
import os
import urllib

import six
from jinja2 import nodes
from random_words import RandomWords


rw = RandomWords()


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


def follow(item):
    if isinstance(item.node, nodes.Getattr):
        for x in follow(item.node):
            yield x
    yield item.attr


def tokenize(node, _dict):
    if isinstance(node, nodes.Output):
        for item in node.nodes:
            tokenize(item, _dict)
    if isinstance(node, nodes.Name):
        _dict[node.name] = rw.random_word()
    if isinstance(node, nodes.If):
        tokenize(node.test, _dict)
        for node in node.body:
            tokenize(node, _dict)
    if isinstance(node, nodes.For):
        data = []
        for node_for in node.body:
            _dict_for = {}
            tokenize(node_for, _dict_for)
            if node.target.name in _dict_for:
                content = _dict_for[node.target.name]
                del _dict_for[node.target.name]
                _dict_for.update(content)
            data.append(_dict_for)
        _dict[node.iter.name] = data
    if isinstance(node, nodes.Call):
        _dict_call = {}
        root, key, last = tokenize(node.node, _dict_call)
        value = 'lambda x: "{}"'.format(rw.random_word())
        last[key] = value
        _dict[root] = last
    if isinstance(node, nodes.Getattr):
        follow_items = list(follow(node))
        if len(follow_items) == 1:
            key = follow_items[0]
            root = node.node.name
            final = {
                key: rw.random_word(),
            }
            _dict.update(final)
            return root, key, final
        base = {}
        current = base
        root = None
        final = {}
        key = None
        for follow_item in follow_items:
            if not root:
                root = follow_item
                continue
            final = current
            current[follow_item] = {}
            current = current[follow_item]
            key = follow_item
        final[key] = rw.random_word()
        _dict[root] = base
        return root, key, final


class JsonGenerator():
    def __init__(self, handler, path):
        self.handler = handler
        self.path = path

    def filepath(self, ext):
        filename = '{}.{}'.format(self.handler.filebase, ext)
        return os.path.join(self.path, filename)

    def feed(self):
        results = {}
        self.handler.file_vars(self.filepath('html'))
        self.handler.prepare_html()
        parsed = self.handler.j2_env.parse(self.handler.html)
        for node in parsed.body:
            tokenize(node, results)
        return results

    def create_file(self):
        filepath = self.filepath('json')
        force = self.handler.cmd_args.force
        save = force and force or not os.path.exists(filepath)
        if save:
            with open(filepath, 'w') as fjson:
                json.dump(self.feed(), fjson, indent=4)

    def generate(self):
        for filename in os.listdir(self.path):
            filepath = os.path.join(self.path, filename)
            self.handler.file_vars(filepath)
            if self.handler.filebase.endswith(self.handler.devpostfix):
                self.create_file()
