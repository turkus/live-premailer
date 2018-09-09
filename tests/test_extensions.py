# -*- coding: utf-8 -*-
import unittest

import pytest
from babel.support import Translations
from jinja2 import Environment, FileSystemLoader

from lpremailer import RenderHandler


translations = Translations.load()


class TestExtensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        j2_loader = FileSystemLoader('.')
        cmd_args = pytest.CmdArgs(loadhistory=False, devpostfix='_dev',
                                  livepostfix='_live', astext=False)
        cls.j2_env = Environment(
            loader=j2_loader, extensions=["jinja2.ext.i18n"])
        cls.j2_env.install_gettext_translations(translations)
        cls.render_handler = RenderHandler(cmd_args)
        cls.render_handler.src_path = '/home/turkus/dummy'

    def test_translations(self):
        def func():
            template = '{{ _("translate") }} {{ gettext("translate") }}'
            template = self.j2_env.from_string(template)
            template.render()
        self.assertTrue(self.render_handler.passed(func))
