import argparse
import logging
import json
import os
import subprocess
import sys
import time

import html2text
from babel.support import Translations
from jinja2 import Environment, FileSystemLoader
from premailer import transform
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler

from .exceptions import ERRORS, LiveBaseError
from .utils import JsonGenerator, parse_params, unquote, object_hook


logging.basicConfig(level=logging.INFO)
translations = Translations.load()

HERE = os.getcwd()

PARSER_INIT = 'init'
PARSER_RUN = 'runserver'

HISTORY_FILENAME = 'lpremailer.history'
HISTORY_FILEPATH = '{}/{}'.format(HERE, HISTORY_FILENAME)


class RenderHandler(FileSystemEventHandler):
    EXT_CSS = '.css'
    EXT_HTML = '.html'
    EXT_JSON = '.json'
    EXTENSIONS = (EXT_CSS, EXT_HTML, EXT_JSON)

    def __init__(self, cmd_args):
        self.cmd_args = cmd_args
        self.src_dir = HERE
        self.history = set()
        self.history_excluded = set()
        if self.cmd_args.loadhistory:
            self.load_history()
        self.devpostfix = self.cmd_args.devpostfix
        self.livepostfix = self.cmd_args.livepostfix
        self.postfixes = (self.livepostfix, self.devpostfix)
        self.j2_loader = FileSystemLoader('.')
        self.j2_env = Environment(
            loader=self.j2_loader, extensions=["jinja2.ext.i18n"])
        self.j2_env.install_gettext_translations(translations)
        self.text_maker = html2text.HTML2Text()
        self.text_maker.ignore_links = True
        self.text_maker.ignore_images = True
        self.funcs_sequence = [self.parse_json, self.prepare_html,
                               self.premail, self.live_html]
        if self.cmd_args.astext:
            self.funcs_sequence.append(self.html_to_txt)

    def on_modified(self, event):
        self.src_dir = HERE

        if event.is_directory:
            return

        filebase, ext = self.filename_splitext(event.src_path)
        if ext not in self.EXTENSIONS:
            return

        if ext != self.EXT_HTML:
            if ext == self.EXT_JSON:
                self.src_dir = os.path.dirname(event.src_path)
                filename = '{}.html'.format(filebase)
                src_path = self.absolute_path(filename)
                self.proceed(src_path)
                return
            if ext == self.EXT_CSS:
                self.history_proceed()
                return

        if filebase.startswith('_'):
            self.history_proceed()
            return

        root = self.filename_root(filebase)
        filename = '{}{}'.format(root, self.devpostfix)
        if filename in self.history:
            return

        if filebase.endswith(self.devpostfix):
            src_dir = os.path.dirname(event.src_path)
            relpath = os.path.relpath(src_dir, HERE)
            self.history.add('{}/{}{}'.format(relpath, filebase, ext))

            self.proceed(event.src_path)
            return

    def history_proceed(self):
        for filename in self.history:
            src_path = self.absolute_path(filename)
            self.proceed(src_path)

    def load_history(self):
        if not os.path.exists(HISTORY_FILEPATH):
            msg = '\nThere is no {} file to load.'
            logging.warning(msg.format(HISTORY_FILENAME))
            return

        missing = set()
        with open(HISTORY_FILEPATH, 'r') as f:
            for filename in f.read().split():
                if filename.startswith('#'):
                    self.history_excluded.add(filename)
                    continue
                filepath = self.absolute_path(filename)
                if os.path.exists(filepath):
                    self.history.add(filename)
                else:
                    missing.add(filepath)
        if missing:
            msg = '\n{} - following files don\'t exist:\n{}\n'
            msg = msg.format(HISTORY_FILENAME, '\n'.join(missing))
            logging.warning(msg)
        if self.history:
            filenames = '\n'.join(self.history)
            msg = '\n\nFollowing filenames from {} loaded:\n{}\n'
            msg = msg.format(HISTORY_FILENAME, filenames)
            logging.info(msg)

    def save_history(self):
        for filename in self.history:
            not_excluded = '#{}'.format(filename)
            if not_excluded in self.history_excluded:
                self.history_excluded.remove(not_excluded)
        filenames = self.history.union(self.history_excluded)
        filenames = '\n'.join(filenames)
        with open(HISTORY_FILEPATH, 'w') as f:
            f.write(filenames)
        filenames = '\n'.join(self.history)
        msg = '\nFollowing filenames saved into {}:\n{}'
        msg = msg.format(HISTORY_FILENAME, filenames)
        logging.info(msg)

    def absolute_path(self, filename):
        return '{}/{}'.format(self.src_dir, filename)

    def filename_root(self, filename):
        root = filename
        for postfix in self.postfixes:
            root = root.replace(postfix, '')
        return root

    def proceed(self, src_path):
        self.file_vars(src_path)
        for func in self.funcs_sequence:
            if not self.passed(func):
                break
        else:
            msg = '\n{}...OK'.format(self.src_path)
            logging.info(msg)

    def file_vars(self, src_path):
        self.src_path = src_path
        self.file_path()
        self.filebase, self.ext = self.filename_splitext(self.src_path)

    def file_path(self):
        self.path = os.path.dirname(self.src_path)

    def filename_splitext(self, src_path):
        filename = os.path.basename(src_path)
        return os.path.splitext(filename)

    def passed(self, func):
        try:
            func()
        except Exception as e:
            ERRORS.get(type(e), LiveBaseError)(e, self.src_path).log()
            return False
        return True

    def parse_json(self):
        json_filename = '{}.json'.format(self.filebase)
        with open(os.path.join(self.path, json_filename), 'r') as fjson:
            self.data = json.load(fjson, object_hook=object_hook)

    def prepare_html(self):
        filepath = os.path.join(self.path, '{}.html'.format(self.filebase))
        with open(filepath, 'rb') as f:
            data = f.read().decode('utf8')
            template = self.j2_env.from_string(data)
            self.html = template.render()

    def premail(self):
        filename = self.filebase.replace(self.devpostfix, '')
        filepath = os.path.join(self.path, '{}.html'.format(filename))
        transformed = transform(self.html)
        unquoted = unquote(transformed)
        encoded = unquoted.encode('utf8')
        with open(filepath, 'wb+') as f:
            f.write(encoded)

    def html_to_txt(self):
        filename = self.filebase.replace(self.devpostfix, '')
        filepath = os.path.join(self.path, '{}_txt.html'.format(filename))
        text = self.text_maker.handle(self.html)
        encoded = text.encode('utf8')
        with open(filepath, 'wb+') as f:
            f.write(encoded)

    def live_html(self):
        filename = '{}{}.html'.format(self.filebase, self.livepostfix)
        filepath = os.path.join(self.path, filename)
        transformed = transform(self.html)
        unquoted = unquote(transformed)
        template = self.j2_env.from_string(unquoted)
        rendered = template.render(**self.data)
        encoded = rendered.encode('utf8')
        with open(filepath, 'wb+') as f:
            f.write(encoded)


class LivePremailer():
    def __init__(self):
        self.observer_paths = {HERE}
        self.bsync_params = {
            'server': None,
            'directory': None,
            'reloadDelay': 1000,
            'online': 'true',
            'logLevel': 'silent',
            'files': HERE,
        }

    def append_arguments(self, parser):
        parser.add_argument('--devpostfix', nargs='?', default='_dev',
                            help='Postfix which should be used to search\
                                  dev templates')
        parser.add_argument('--livepostfix', nargs='?', default='_live',
                            help='Postfix which should be used to name\
                                  files with live preview')
        parser.add_argument('--loadhistory', action='store_true',
                            help='lpremailer will load all paths located\
                                  in {} file to memory and rerender them\
                                  everytime change in any file occurs'
                                  .format(HISTORY_FILENAME))
        parser.add_argument('--savehistory', action='store_true',
                            help='lpremailer will save all dev file paths\
                                  recorded during development in {} file'
                                  .format(HISTORY_FILENAME))
        parser.add_argument('--astext', action='store_true',
                            help='lpremailer will save all dev files\
                                  as simple txt messages')

    def parse_args(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        runserver_help = 'Runs server for live premailer'
        sub_parser = subparsers.add_parser(PARSER_RUN, help=runserver_help)
        sub_parser.set_defaults(which=PARSER_RUN)
        sub_parser.add_argument('--staticdir', nargs='?',
                                help='Path to directory where static folder\
                                      is located')
        self.append_arguments(sub_parser)
        init_help = 'Create json files for htmls with provided\
                     postfix in current directory'
        sub_parser = subparsers.add_parser(PARSER_INIT, help=init_help)
        sub_parser.set_defaults(which=PARSER_INIT)
        sub_parser.add_argument('--force', action='store_true',
                                help='Overwrites json files')
        self.append_arguments(sub_parser)

        self.args = parser.parse_args()

    def json_files(self):
        handler = RenderHandler(self.args)
        if self.args.which == PARSER_INIT:
            JsonGenerator(handler, HERE).generate()
            for root, dirs, files in os.walk(HERE):
                for _dir in dirs:
                    path = os.path.join(root, _dir)
                    JsonGenerator(handler, path).generate()
            sys.exit(1)

    def start_observer(self):
        self.observer = PollingObserver()
        self.observer.should_keep_running()
        self.observer.handler = RenderHandler(self.args)
        for path in self.observer_paths:
            self.observer.schedule(self.observer.handler,
                                   path, recursive=True)
        self.observer.start()

    def update_params(self):
        if not os.path.exists(self.args.staticdir):
            logging.warning('Static files won\'t be maintained/served.')
            return
        files = '!**/*.less,!**/*.sass,!**/*.scss'
        files = (self.bsync_params['files'], self.args.staticdir, files)
        self.bsync_params['files'] = ','.join(files)
        self.bsync_params['ss'] = self.args.staticdir
        self.observer_paths.add(self.args.staticdir)

    def bsync_command(self):
        return 'browser-sync start {}'\
               .format(parse_params(self.bsync_params))

    def run_bsync(self):
        self.bsync = subprocess.Popen(self.bsync_command(), shell=True)

    def run(self):
        self.parse_args()
        self.json_files()
        self.update_params()
        self.start_observer()
        self.run_bsync()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            if self.args.savehistory:
                self.observer.handler.save_history()
            self.observer.stop()
            self.bsync.kill()
        self.observer.join()


def main():
    LivePremailer().run()
