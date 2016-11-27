# -*- coding: utf-8 -*-
import json
import logging
import unittest

import pytest
import six
from jinja2 import Environment, FileSystemLoader
from premailer import transform

from lpremailer import RenderHandler
from lpremailer.exceptions import (LiveAttributeError, LiveExternalNotFoundError,
                                   LiveJSONDecodeError, LiveTemplateNotFound,
                                   LiveTemplateSyntaxError, LiveUndefinedError,
                                   LiveUnicodeDecodeError, LiveUnicodeEncodeError,
                                   LiveValueError)
from lpremailer.utils import object_hook


class TestErrors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        j2_loader = FileSystemLoader('.')
        cmd_args = pytest.CmdArgs(loadhistory=False, devpostfix='_dev',
                                  livepostfix='_live', astext=False)
        cls.j2_env = Environment(loader=j2_loader)
        cls.render_handler = RenderHandler(cmd_args)
        cls.render_handler.src_path = '/home/turkus/dummy'
        cls.logging_error = logging.error
        logging.error = cls._var_log

    @classmethod
    def tearDownClass(cls):
        logging.error = cls.logging_error

    @classmethod
    def _var_log(cls, msg):
        cls.logger = msg

    def test_attribute(self):
        def func():
            template = '{{ func() }}'
            template = self.j2_env.from_string(template)
            template.render({'func': 'value'})
        self.assertFalse(self.render_handler.passed(func))
        self.assertIn(LiveAttributeError.MSG, self.logger)

    def test_external_not_found(self):
        def func():
            template = '<link rel="stylesheet" href="mail.css"/>'
            transform(template)
        self.assertFalse(self.render_handler.passed(func))
        self.assertIn(LiveExternalNotFoundError.MSG, self.logger)

    def test_template_not_found(self):
        template = "{% include 'not_exists.html' %}"
        template = self.j2_env.from_string(template)
        self.assertFalse(self.render_handler.passed(template.render))
        self.assertIn(LiveTemplateNotFound.MSG, self.logger)

    def test_template_syntax(self):
        def func():
            template = '{%'
            template = self.j2_env.from_string(template)
        self.assertFalse(self.render_handler.passed(func))
        self.assertIn(LiveTemplateSyntaxError.MSG, self.logger)

    def test_undefined(self):
        def func():
            template = '{{ obj.name }}'
            template = self.j2_env.from_string(template)
            template.render({})
        self.assertFalse(self.render_handler.passed(func))
        self.assertIn(LiveUndefinedError.MSG, self.logger)

    def test_value(self):
        def func():
            template = self.j2_env.from_string('')
            template.render('obj')
        self.assertFalse(self.render_handler.passed(func))
        self.assertIn(LiveValueError.MSG, self.logger)

    def test_encode(self):
        if six.PY3:
            return

        def func():
            copyright = u'©'
            with open('/tmp/lpremailer.html', 'w') as f:
                f.write(copyright)
        self.assertFalse(self.render_handler.passed(func))
        self.assertIn(LiveUnicodeEncodeError.MSG, self.logger)

    def test_decode(self):
        if six.PY3:
            return

        def func():
            self.j2_env.from_string('\xa9')
        self.assertFalse(self.render_handler.passed(func))
        self.assertIn(LiveUnicodeDecodeError.MSG, self.logger)

    def test_json_decode(self):
        def func():
            _json = "{'copyright': '\xa9'}"
            json.loads(_json, object_hook=object_hook)
        self.assertFalse(self.render_handler.passed(func))
        if six.PY3:
            self.assertIn(LiveJSONDecodeError.MSG, self.logger)
        else:
            self.assertIn(LiveValueError.MSG, self.logger)
