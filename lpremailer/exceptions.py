import logging

import six
from jinja2.exceptions import (
        TemplateNotFound, TemplateSyntaxError, UndefinedError)
from premailer.premailer import ExternalNotFoundError


logging.basicConfig(level=logging.INFO)


class LiveBaseError():
    MSG = """
    Whooops! I don\'t handle this kind of an execption.
    Please be so kind and create an issue about at:
    https://github.com/turkus/live-premailer/issues

    Thanks,
    turkus
    """

    def __init__(self, e, src_path):
        self.e = e
        self.src_path = src_path

    def log(self):
        msg = self.live_message()
        logging.error(msg)

    def unhandled_error(self):
        return self.MSG == LiveBaseError.MSG

    @property
    def base_msg(self):
        if self.unhandled_error():
            return type(self.e)
        if hasattr(self.e, 'message'):
            return self.e.message
        return ', '.join(self.e.args)

    def live_message(self):
        msg = '\n{{}}\n{}\n{{}}\n'.format(self.MSG)
        return msg.format(self.src_path, self.base_msg)


class LiveAttributeError(LiveBaseError):
    MSG = 'Bad value for key in your json:'


class LiveTypeError(LiveBaseError):
    MSG = 'Wrong type of a value:'


class LiveValueError(LiveBaseError):
    MSG = 'Your json file is invalid:'


class LiveExternalNotFoundError(LiveBaseError):
    MSG = 'Included file or path doesn\'t exist:'


class LiveTemplateNotFound(LiveBaseError):
    MSG = 'Following template not found:'


class LiveTemplateSyntaxError(LiveBaseError):
    MSG = 'Something is wrong with your template:'


class LiveUndefinedError(LiveBaseError):
    MSG = 'One of variables is missing in your json:'


class LiveUnicodeDecodeError(LiveBaseError):
    MSG = """
    I encountered a decoding error:
    UnicodeDecodeError: 'ascii' codec can't decode byte...
    please revert your last change, hope that helps :)
    """


class LiveUnicodeEncodeError(LiveBaseError):
    MSG = """
    I encountered an encoding error:
    UnicodeEncodeError: 'ascii' codec can't encode byte...
    please revert your last change, hope that helps :)
    """


class LiveJSONDecodeError(LiveBaseError):
    MSG = 'Your json file is invalid:'

    def live_message(self):
        msg = '\n{}\n{}\n{}: line {} column {} char({})\n'
        return msg.format(self.src_path, self.MSG, self.e.msg, self.e.lineno,
                          self.e.colno, self.e.pos)


ERRORS = {
    AttributeError: LiveAttributeError,
    ExternalNotFoundError: LiveExternalNotFoundError,
    TemplateNotFound: LiveTemplateNotFound,
    TemplateSyntaxError: LiveTemplateSyntaxError,
    TypeError: LiveTypeError,
    UndefinedError: LiveUndefinedError,
    UnicodeDecodeError: LiveUnicodeDecodeError,
    UnicodeEncodeError: LiveUnicodeEncodeError,
    ValueError: LiveValueError,
}
if six.PY3:
    try:
        from json.decoder import JSONDecodeError
        ERRORS[JSONDecodeError] = LiveJSONDecodeError
    except ImportError:
        pass
