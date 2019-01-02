Live premailer
==============

[![Build Status](https://travis-ci.org/turkus/live-premailer.svg?branch=master)](https://travis-ci.org/turkus/live-premailer)
[![PyPI Version](https://img.shields.io/pypi/v/live-premailer.svg)](https://pypi.python.org/pypi/live-premailer)

<pre>
<table>
  <tr>
    <td>Info:</td>
    <td>Live premailer for jinja2 templates</td>
  <tr/>
  <tr>
    <td>Repository:</td>
    <td><a href="https://github.com/turkus/live-premailer">https://github.com/turkus/live-premailer</a></td>
  <tr/>
  <tr>
    <td>Author:</td>
    <td>Wojciech Rola</td>
  <tr/>
  <tr>
    <td>Maintainer:</td>
    <td>Wojciech Rola</td>
  <tr/>
</table>
</pre>

Why live?
---------

Everytime we want to create and test mail templates, where Jinja2 template engine is in use, we need to send them to see how it looks like. It's really annoying. So that's why this package exists.
``live-premailer`` package is for testing our mail frontend live, without sending unnecessary emails.

[![LIVE DEMO](https://docs.google.com/uc?id=0Byh5x9fIozwxaGJKZFpqazFDREE)](https://drive.google.com/open?id=0Byh5x9fIozwxdjZYRGdfakplOUU)


Installation
------------

```bash
$ pip install live-premailer
```

To provide live preview we need to install also:

```bash
$ sudo npm install browser-sync@2.26.3 -g
```

On the linux distributions make sure you have `python-dev` (py2) or `python3-dev` (py3) installed - according to the python version you use:

```bash
$ sudo apt-get install python-dev
```

Let's do it!
------------

Let's consider this simple application structure (full example [here](https://github.com/turkus/live-premailer/tree/master/examples)):

```
myproject
├── static
│   ├── css
│   │   └── mail.css
│   ├── img
│   │   └── logo.jpg
│   └── js
└── templates
    └── mail
        ├── greetings_dev.html
        ├── _mail_footer.html
        └── _mail_header.html
```

And following templates:

``_mail_header.html``

```html
{% raw %}
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
    <link rel="stylesheet" href="../../static/css/mail.css"/>
</head>
    <body>
        <table class="container">
            <tr class="header">
                <td class="logo">
                    <a href="http://python.org">
                        <img src="{{ request.static_url('static/img/mail/logo.jpg') }}" alt="Live premailer">
                    </a>
                </td>
            </tr>
            <tr>
{% endraw %}
```

``greetings_dev.html``

```html
{% include '_mail_header.html' %}
{% raw %}
<td class="main-content" colspan="2">
    <table>
        <tr>
            <td class="hi">Hello {{ name }}!</td>
        </tr>
    </table>
</td>
{% endraw %}
{% include '_mail_footer.html' %}
```

``_mail_footer.html``

```html
{% raw %}
            </tr>
            <tr>
                <td>© Copyright - turkus</td>
            </tr>
        </table>
    </body>
</html>
{% endraw %}
```

You have to remember that live premailer script operates in path where is executed. So if you want to create premailed template you have to be in the console under the same path where your dev templates exists, so:

```
myproject
├── static
│   ├── css
│   │   └── mail.css
│   ├── img
│   │   └── logo.jpg
│   └── js
└── templates
    └── mail <---- in our case here
        ├── greetings_dev.html <---- because that's a dev template
        ├── _mail_footer.html
        └── _mail_header.html
```

```bash
$ cd myproject/templates/mail
```
At the beginning we need to run init:

```bash
$ lpremailer init
```

after that operation for each ``<template>_dev.html`` json file with template feed would be generated. So our ``templates`` directory structure should look like this:

```
└── templates
    └── mail
        ├── greetings_dev.html
        ├── greetings_dev.json
        ├── _mail_footer.html
        └── _mail_header.html
```

Json files are for json representation of variables which occur in templates when using jinja2 as template engine.

Next step is run simple server based on ``browsersync`` package:

```bash
$ lpremailer runserver --staticdir=/home/turkus/programming/myproject 
```

``--staticdir`` is an option needed for css files which dev templates use and for displaying images, because browsers don't allow to do it (CORS). It should point to path where ``static`` directory is located.

After that operation browser should run and display listing of all files in current directory. At this point we don't have our "live" html to preview. To do that please follow next steps.

We see that we have in our ``greetings_dev.html`` variable ``{{ name }}``, but we have also in our ``_mail_header.html`` a function called ``request.static_url('static/img/logo.jpg')``.  

So let's take a look at json file ``greetings_dev.json``:

```json
{
    "name": "turkus",
    "request": {
        "static_url": "lambda x: \"something\""
    }
} 
```

When we are talking about simple variables like strings, numbers everything is obvious, but when we have a function, sometimes we pass different arguments, especially when serving statics. 

So what python ``lambda`` does here?

To clarifying let's change it to:

```json
{
    "name": "turkus",
    "request": {
        "static_url": "lambda img_path: img_path"
    }
} 
```

Now, it just takes argument and returns it, so in "live" template instead of:

```html
<img src="request.static_url('static/img/logo.jpg')" alt="Live premailer" width="128" height="33">
```

we will see:

```html
<img src="static/img/logo.jpg" alt="Live premailer" width="128" height="33">
```

After saving data in ``greetings_dev.json`` browser will reload directory listing page and you will see ``greetings_dev_live.html`` generated which is live mail preview and ``greetings.html`` as a final version of premailed template with all jinja2 variables and expressions ready to send by your app. 

So for developing you can go to (or click ``greetings_dev_live.html`` on a browser page):

[http://localhost:3000/greetings_dev_live.html](http://localhost:3000/greetings_dev_live.html)

and see the result. 

Each edit of ``greetings_dev.html``, ``greetings.json`` and static files rebuilds mail templates and reloads preview.

Debug
-----

Console will inform you about each error in human-readable way:

```
One of variables is missing in your json:
'request' is undefined
```

or tell you that everything is fine:

```
/home/turkus/programming/myproject/templates/mail/greetings_dev.html...OK
```

Configuration
-------------

### Json files generation
If you want to overwrite existing json files, use ``--force`` option:


```bash
$ lpremailer init --force
```

### Postfixes

You can define your own devpostfix (default is ``_dev``) and livepostfix (default is ``_live``), by using proper options:

```bash
$ lpremailer init --devpostfix=_whateverdev
```
and according to init:

```bash
$ lpremailer runserver --staticdir=/home/turkus/programming/myproject --devpostfix=_whateverdev --livepostfix=_whateverlive
```

### History

To rerender mail templates when editing css or templates they include, you have to add to cache some dev templates. You can do it by saving once one of the dev templates first and then operate on css or templates it includes OR you can use following parameters:

 - ``--loadhistory`` - if you have ``lpremailer.history`` located in directory where you run ``lpremailer``, then it loads all filenames from it to the cache
 - ``--savehistory`` - everytime you "exit" ``lpremailer`` (CTRL+C) all dev template filenames stored in a cache will be saved in ``lpremailer.history`` file

```bash
$ lpremailer runserver --staticdir=/home/turkus/programming/myproject --loadhistory --savehistory
```

so using these parameters ``lpremailer`` will rerender all templates which dev representation is stored cache.

Example of ``/home/turkus/programming/myproject/templates/mail/lpremailer.history`` file:

```
greetings_dev.html
```

You can also exclude some files from parsing using ``#`` on the beginning of line with dev template filename:

```
greetings_dev.html
#excluded_dev.html
```

### Save email templates as text messages
If you want to generate text version of your email use ``--astext`` option:


```bash
$ lpremailer runserver --staticdir=/home/turkus/programming/myproject --astext
```

According to our main example you will get the ``greetings_txt.html`` file in the directory you operate. It takes place after saving a ``greetings_dev.html`` file or any connected with (if ``greetings_dev.html`` occurs in the ``lpremailer.history`` file or had been loaded to the cache).

Troubleshooting
---------------

If you run init with custom devpostfix then use the same when running server. Otherwise it won't work.

For including templates there is a need to use underscore ``_``, so as in the example above we should do it in this way: ``_mail_header.html``.

Remember about put all jinja2 variables and expressions in ``{% raw %}{% endraw %}`` container. Excluding ``{% extends .. %}`` and ``{% include ... %}`` (see examples above).
