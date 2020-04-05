import ast
import re
from setuptools import setup


_version_re = re.compile(r'__version__\s+=\s+(.*)')


with open('lpremailer/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))


setup(
    name='live-premailer',
    packages=['lpremailer'],
    version=version,
    description='Live premailer for jinja2 templates',
    author='turkus',
    author_email='wojciechrola@wp.pl',
    url='https://github.com/turkus/live-premailer',
    download_url='https://github.com/turkus/live-premailer/tarball/{}'.format(version),
    keywords=['live', 'browsersync', 'jinja2', 'premailer'],
    entry_points={
        'console_scripts': [
            'lpremailer = lpremailer.main:main',
        ]
    },
    install_requires=[
        'jinja2', 'premailer', 'watchdog', 'six', 'RandomWords',
        'html2text', 'Babel'
    ],
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
