# -*- coding: utf-8 -*-

import ast
import sys
import collections
import traceback

from django.utils.six import exec_
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Line(collections.namedtuple('Line', ['ast', 'original'])):
    @classmethod
    def build(cls, original):
        stripped = original.strip()

        if stripped.startswith('_ '):
            _, stripped = stripped.split(' ', 1)
            stripped = '{{x: y for x, y in ({}).__dict__.items() if not x.startswith("__")}}'.format(stripped)
        elif stripped.startswith('__ '):
            _, stripped = stripped.split(' ', 1)
            stripped = '({}).__dict__'.format(stripped)

        try:
            parsed = ast.parse(stripped, mode='eval')
            return Expression(parsed, original)
        except SyntaxError:
            try:
                parsed = ast.parse(stripped)
            except SyntaxError as e:
                return MisformattedStatement(e, original)
            return Statement(parsed, original)

    def __str__(self):
        return u'>>> {}'.format(self.original)


class Statement(Line):
    def __call__(self, globals, locals):
        previous = locals.copy()
        exec_(self.code, globals, locals)
        return self._find_changes(previous, locals)

    def _find_changes(self, previous, current):
        changes, additions = {}, {}
        for k, v in current.items():
            if k not in previous:
                additions[k] = v
            elif previous[k] != v:
                changes[k] = (previous[k], v)
        return Success(self, additions, changes)

    @property
    def code(self):
        return compile(self.ast, u'<string>', 'exec')


class Expression(Line):
    def __call__(self, globals, locals):
        return Evaluation(self, eval(self.code, globals, locals))

    @property
    def code(self):
        return compile(self.ast, self.original, 'eval')


@python_2_unicode_compatible
class MisformattedStatement(Line):
    def __call__(self, globals, locals):
        raise self.ast

    def __str__(self):
        return u'{}\n{}'.format(self.original, self.ast)


@python_2_unicode_compatible
class Failed(collections.namedtuple('Failed', ['line', 'error'])):
    def __str__(self):
        return str(self.error)


@python_2_unicode_compatible
class Success(collections.namedtuple('Success', ['line', 'additions', 'changes'])):
    def __str__(self):
        buff = []
        for k, v in sorted(self.additions.items()):
            buff.append(u'    {}: {!r}'.format(k, v))
        for k, (v1, v2) in sorted(self.changes.items()):
            buff.append(u'    {}: {!r} -> {!r}'.format(k, v1, v2))
        return u'\n'.join(buff)


@python_2_unicode_compatible
class Evaluation(collections.namedtuple('Evaluation', ['line', 'evaluation'])):
    @property
    def evaluation_repr(self):
        if isinstance(self.evaluation, dict):
            return '{\n%s    }' % ''.join('        {!r}: {!r},\n'.format(*args) for args in self.evaluation.items())
        return repr(self.evaluation)

    def __str__(self):
        return '    ' + self.evaluation_repr


class Executor(object):
    """
    A step by step python code executor.

    It executes line by line a line of instructions separated by a ; and yields
    a detailled version of the results of the operation.
    """

    def __init__(self, statements):
        self._locals = {}
        self._globals = globals()
        self._code = [Line.build(line) for line in statements]

    def __iter__(self):
        for code in self._code:
            yield ExecutionStep(code, self._globals, self._locals)


@python_2_unicode_compatible
class ExecutionStep(object):
    def __init__(self, code, globals_, locals_):
        self.code = code
        self.globals_ = globals_
        self.locals_ = locals_
        self._failed = None

    def __str__(self):
        return str(self.code)

    def __call__(self):
        try:
            self.failed = False
            return self.code(self.globals_, self.locals_)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = u''.join(traceback.format_tb(exc_traceback) +
                          ['   ', self.code.original, u'\n'] +
                          traceback.format_exception_only(exc_type, exc_value))
            self.failed = True
            return Failed(self.code, tb)
