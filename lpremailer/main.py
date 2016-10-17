import argparse
import logging
import json
import os
import subprocess
import sys
import time

import six
from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from jinja2.exceptions import (
        TemplateNotFound, TemplateSyntaxError, UndefinedError)
from premailer import transform
from premailer.premailer import ExternalNotFoundError
from six import string_types
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler


logging.basicConfig(level=logging.INFO)


HERE = os.getcwd()
PARSER_INIT = 'init'
PARSER_RUN = 'runserver'

HISTORY_FILENAME = 'lpremailer.history'
HISTORY_FILEPATH = '{}/{}'.format(HERE, HISTORY_FILENAME)

ERRORS = {
    AttributeError: 'Bad value for key in your json:',
    ExternalNotFoundError: 'Included file or path doesn\'t exist:',
    TemplateNotFound: 'Following template not found:',
    TemplateSyntaxError: 'Something is wrong with your template:',
    UndefinedError: 'One of variables is missing in your json:',
    ValueError: 'Your json file is invalid:',
}


## UTILS ##
def parse_params(params):
    return ' '.join((
        '--{}={}'.format(key, value) if value else '--{}'.format(key)
        for key, value in params.items()))


def object_hook(obj):
    result = {}
    for key, value in obj.items():
        if isinstance(value, string_types) and u'lambda' in value:
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


## MAIN ##
class RenderHandler(FileSystemEventHandler):
    EXT_CSS = '.css'
    EXT_HTML = '.html'
    EXT_JSON = '.json'
    EXTENSIONS = (EXT_CSS, EXT_HTML, EXT_JSON)

    def __init__(self, cmd_args):
        self.history = set()
        if cmd_args.loadhistory:
            self.load_history()
        self.devpostfix = cmd_args.devpostfix
        self.livepostfix = cmd_args.livepostfix
        self.postfixes = (self.livepostfix, self.devpostfix)
        self.j2_loader = FileSystemLoader('.')
        self.j2_env = Environment(loader=self.j2_loader)
        self.funcs_sequence = [self.parse_json, self.prepare_html,
                               self.premail, self.live_html]

    def on_modified(self, event):
        if event.is_directory:
            return

        filebase, ext = self.filename_splitext(event.src_path)
        if ext not in self.EXTENSIONS:
            return

        if ext != self.EXT_HTML:
            if ext == self.EXT_JSON:
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
            self.history.add('{}{}'.format(filebase, ext))
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
        with open(HISTORY_FILEPATH, 'w') as f:
            filenames = '\n'.join(self.history)
            f.write(filenames)
        filenames = '\n'.join(self.history)
        msg = '\nFollowing filenames saved into {}:\n{}'
        msg = msg.format(HISTORY_FILENAME, filenames)
        logging.info(msg)

    def absolute_path(self, filename):
        return '{}/{}'.format(HERE, filename)

    def filename_root(self, filename):
        root = filename
        for postfix in self.postfixes:
            root = root.replace(postfix, '')
        return root

    def proceed(self, src_path):
        self.src_path = src_path
        self.file_vars()
        for func in self.funcs_sequence:
            if not self.passed(func):
                break
        else:
            msg = '\n{}...OK'.format(self.src_path)
            logging.info(msg)

    def file_vars(self):
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
            error_type = type(e)
            if six.PY3:
                from json.decoder import JSONDecodeError
                if error_type == JSONDecodeError:
                    info = 'Your json file is invalid:'
                    msg = '\n{}\n{}\n{}: line {} column {} char({})\n'
                    msg = msg.format(self.src_path, info, e.msg, e.lineno,
                                     e.colno, e.pos)
                    logging.error(msg)
                    return False
            if hasattr(e, 'message'):
                e_message = e.message
            else:
                e_message = ', '.join(e.args)
            msg = ERRORS.get(error_type)
            msg = '\n{{}}\n{}\n{{}}\n'.format(msg)
            msg = msg.format(self.src_path, e_message)
            logging.error(msg)
            return False
        return True

    def parse_json(self):
        json_filename = '{}.json'.format(self.filebase)
        with open(os.path.join(self.path, json_filename), 'r') as fjson:
            self.data = json.load(fjson, object_hook=object_hook)

    def prepare_html(self):
        filepath = os.path.join(self.path, '{}.html'.format(self.filebase))
        with open(filepath, 'r') as f:
            template = self.j2_env.from_string(f.read())
            self.html = template.render()

    def premail(self):
        filename = self.filebase.replace(self.devpostfix, '')
        filepath = os.path.join(self.path, '{}.html'.format(filename))
        transformed = transform(self.html)
        with open(filepath, 'w+') as f:
            f.write(transformed)

    def live_html(self):
        filename = '{}{}.html'.format(self.filebase, self.livepostfix)
        filepath = os.path.join(self.path, filename)
        template = self.j2_env.from_string(self.html)
        rendered = template.render(**self.data)
        transformed = transform(rendered)
        with open(filepath, 'w+') as f:
            f.write(transformed)


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

    def parse_args(self):
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        runserver_help = 'Runs server for live premailer'
        sub_parser = subparsers.add_parser(PARSER_RUN, help=runserver_help)
        sub_parser.set_defaults(which=PARSER_RUN)
        sub_parser.add_argument('--staticdir', nargs='?',
                                help='Path to directory where static folder\
                                      is located')
        sub_parser.add_argument('--devpostfix', nargs='?', default='_dev',
                                help='Postfix which should be used to search\
                                      dev templates')
        sub_parser.add_argument('--livepostfix', nargs='?', default='_live',
                                help='Postfix which should be used to name\
                                      files with live preview')
        sub_parser.add_argument('--loadhistory', action='store_true',
                                help='lpremailer will load all paths located\
                                      in {} file to memory and rerender them\
                                      everytime change in any file occurs'
                                      .format(HISTORY_FILENAME))
        sub_parser.add_argument('--savehistory', action='store_true',
                                help='lpremailer will save all dev file paths\
                                      recorded during development in {} file'
                                      .format(HISTORY_FILENAME))

        init_help = 'Create json files for htmls with provided\
                     postfix in current directory'
        sub_parser = subparsers.add_parser(PARSER_INIT, help=init_help)
        sub_parser.set_defaults(which=PARSER_INIT)
        sub_parser.add_argument('--devpostfix', nargs='?', default='_dev',
                                help='Postfix which should be used to search\
                                      dev templates')
        self.args = parser.parse_args()

    def json_files(self):
        if self.args.which == PARSER_INIT:
            JsonGenerator(self.args.devpostfix).generate()
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
