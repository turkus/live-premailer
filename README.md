Live premailer
==============

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

Installation
------------

```bash
$ pip install live-premailer
```

To provide live preview we need to install also:

```bash
$ sudo npm install browser-sync@2.17.2 -g
```

Let's do it!
------------

Let's consider this simple application structure:

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
                    <a href="http://example.com">
                        <img src="{{ request.static_url('static/img/mail/logo.jpg') }}" alt="Live premailer" width="128" height="33">
                    </a>
                </td>
                <td class="url"><a href="http://example.com">example.com</a></td>
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
                Copyright - turkus
            </tr>
        </table>
    </body>
</html>
{% endraw %}
```

You have to remember that live premailer script operates in path where is executed. So if you want to create premailed template you have to be in the console under the same path where your devs templates exists, so:

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
        ├── greetings_dev.html
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

after that operation for each ``<template>_dev.html`` json file will be created. So our templates directory structure looks like this:

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

``--staticdir`` is an option needed for displaying images, because browsers don't allow to do it (CORS). It should point to path where ``static`` directory is located.

After that operation browser should run and display listing of all files in current directory. At this point we don't have our "live" html to preview. To do that please follow next steps.

We see that we have in our ``greetings_dev.html`` variable ``{{ name }}``, but we have also in our ``_mail_header.html`` a function called ``request.static_url('static/img/logo.jpg')``.  

So how to handle it? Just by editing json file ``greetings_dev.json``:

```json
{
    "name": "turkus",
    "request": {
        "static_url": "lambda img_path: img_path"
    }
} 
```

Now focus! When we are talking about simple variables like strings, numbers everything is obvious, but when we have a function, sometimes we pass different arguments, especially when serving statics. 

So what python ``lambda`` does here?
In our case it just takes argument and returns it. So in "live" template instead of:

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

and see the result. Each edit of ``greetings_dev.html`` and ``greetings.json`` file reloads preview.

If you will see:

**Parsing failed! Please check console and fix errors.**

console will inform you which variable/function is missing in json file:

```
Missing in your json file: request
```

After completing all variables in your json file your live preview will adjust these changes automatically.

Configuration
-------------

You can define your own devpostfix (default is ``_dev``) and livepostfix (default is ``_live``), by using proper options:

```bash
$ lpremailer init --devpostfix=_whateverdev
```
and according to init:

```bash
$ lpremailer runserver --staticdir=/home/turkus/programming/myproject --devpostfix=_whateverdev --livepostfix=_whateverlive
```

Troubleshooting
---------------

If you run init with custom devpostfix then use the same when running server. Otherwise it won't work.

Remember about put all jinja2 variables and expressions in ``{% raw %}{% endraw %}`` container. Excluding ``{% extends .. %}`` and ``{% include ... %}`` (see examples above).


To be continued...
------------------

- rerender templates which include other templates after their edit
- rerender after editing css files
- create instant schema in json files according to variables in templates
- bulk render
- use other template engines
