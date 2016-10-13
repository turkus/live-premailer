import argparse
import logging
import json
import os
import subprocess
import sys
import time

from jinja2 import FileSystemLoader
from jinja2.environment import Environment
from jinja2.exceptions import TemplateSyntaxError, UndefinedError
from premailer import transform
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler


logging.basicConfig(level=logging.INFO)


HERE = os.getcwd()
PARSER_INIT = 'init'
PARSER_RUN = 'runserver'

DEV_HISTORY = set()
ERRORS = {
    AttributeError: '\nBad value for key in your json:\n{}\n',
    ValueError: 'Your json file is invalid:\n{}\n',
    TemplateSyntaxError: '\nSomething is wrong with your template:\n{}\n',
    UndefinedError: '\nOne of variables is missing in your json::\n{}\n',
}


## UTILS ##
def parse_params(params):
    return ' '.join((
        '--{}={}'.format(key, value) if value else '--{}'.format(key)
        for key, value in params.items()))


def object_hook(obj):
    result = {}
    for key, value in obj.items():
        if type(value) == unicode and 'lambda' in value:
            result[key] = eval(value)
        else:
            result[key] = value
    return result


def handle_errors(f):
    try:
        f()
    except Exception as e:
        msg = ERRORS.get(type(e))
        logging.error(msg.format(e.message))
        return False
    return True


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
    RELOAD_ON_EXT = ('.html', '.json')

    def __init__(self, cmd_args):
        self.devpostfix = cmd_args.devpostfix
        self.livepostfix = cmd_args.livepostfix
        self.j2_loader = FileSystemLoader('.')
        self.j2_env = Environment(loader=self.j2_loader)
        self.f_sequence = [
                self.parse_json, self.prepare_html, self.premail, self.live_html]

    def on_modified(self, event):
        self.event = event
        self.path = os.path.dirname(self.event.src_path)
        self.filename_splitext()

        if not self.event.is_directory and self.filebase.endswith(self.devpostfix)\
           and self.ext in self.RELOAD_ON_EXT:
            for f in self.f_sequence:
                if not handle_errors(f):
                    break
            else:
                logging.info('\nEverything is OK')

    def filename_splitext(self): 
        filename = os.path.basename(self.event.src_path)
        self.filebase, self.ext = os.path.splitext(filename)

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
    BSYNC_PARAMS = {
        'server': None,
        'directory': None,
        'reloadDelay': 1000,
        'online': 'true',
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

    def observe_paths(self):
        return self.BSYNC_PARAMS['files'].split(',')

    def start_observer(self):
        paths = self.observe_paths()
        self.observer = PollingObserver()
        self.observer.should_keep_running()
        for path in paths:
            self.observer.schedule(RenderHandler(self.args), path, recursive=True)
        self.observer.start()

    def update_bsync_params(self):
        if not os.path.exists(self.args.staticdir):
            logging.warning('Static files won\'t be maintained/served.')
            return
        files = ','.join((self.BSYNC_PARAMS['files'], self.args.staticdir))
        self.BSYNC_PARAMS['files'] = files
        self.BSYNC_PARAMS['ss'] = self.args.staticdir

    def bsync_command(self):
        return 'browser-sync start {}'.format(parse_params(self.BSYNC_PARAMS))

    def run_bsync(self):
        self.bsync = subprocess.Popen(self.bsync_command(), shell=True)

    def run(self):
        self.parse_args()
        self.json_files()
        self.update_bsync_params()
        self.start_observer()
        self.run_bsync()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            self.bsync.kill()
        self.observer.join()


def main():
    LivePremailer().run()
