# -*- coding: utf-8 -*-

import ast
import sys
import collections
import traceback

from django.utils.six import exec_, text_type
from django.utils.encoding import python_2_unicode_compatible
from django.core.management import BaseCommand


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


def parse(input):
    if not isinstance(input, text_type):
        input = input.decode(sys.getfilesystemencoding())
    input = input.strip()
    if '\n' not in input:
        return input.split(u';')

    all_lines = []
    buffer = []
    for line in input.split('\n'):
        if buffer and not line.startswith((' ', '\t')):
            all_lines.append(';'.join(buffer))
            buffer = []
        buffer.append(line)
    all_lines.append(';'.join(buffer))
    return all_lines


class Command(BaseCommand):
    """
    Execute a snippet.

    This commands takes a list of python instructions and executes it, one at a
    time showing the results. The valid instructions are single lines or 2
    lines blocks.

    The line can be either an expression or a generic statement. Expressions
    (at the AST meaning) do not intend to modify the locals variables and are
    queries of the local state. They print the evaluation of the expression.
    The rest of the statements are executed and the modifications made to the
    locals variables are printed (variables added, and variables being changed)

    The lines are all parsed before execution and SyntaxErrors are raised
    before running. When the ``-c|--continue`` flag is enabled, the execution
    continues if an exceptions occurs.

    $ manage.py exec 'import sys; sys.version; sys, abc = None, sys'
    >>> import sys
        sys: <module 'sys' (built-in)>
    >>>  sys.version
        2.7.10 (default, Sep  7 2015, 13:51:49)
    [GCC 5.2.0]
    >>>  sys, abc = None, sys
        abc: <module 'sys' (built-in)>
        sys: <module 'sys' (built-in)> -> None

    Exceptions and their tracebacks are printed

    $ ./manage.py exec 'open("/tmp/abc", "G")'
    >>> open("/tmp/abc", G)
    Traceback (most recent call last):
    File "sett/shell.py", line 101, in __call__
        yield code(self._globals, self._locals)
    File "sett/shell.py", line 64, in __call__
        return Evaluation(self, eval(self.code, globals, locals))
    File "open("/tmp/abc", "G")", line 1, in <module>
    ValueError: mode string must begin with one of 'r', 'w', 'a' or 'U', not 'G'

    Exec can handle simple 2 lines if, with, for, ... blocks.
    $ ./manage.py exec 'for x in "abc": print(x)'
    a
    b
    c
    >>> for x in "abc": print(x)
        x: c

    Python statements can also be piped from the stdin or from a file. When the
    command is only ``-``, then the standard input is read then executed. If
    the instruction starts with ``/`` or ``./``, then this file is opened and
    executed.
    """

    def __init__(self, *args, **kw):
        self.stdin = kw.pop('stdin', sys.stdin)
        super(Command, self).__init__(*args, **kw)

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('cmd')
        parser.add_argument('-c',
                            '--contine',
                            dest='stop_at_exception',
                            help='Continue when an exception is raised',
                            action='store_false',
                            default=True,
                            )

    def handle(self, cmd, stop_at_exception=False, **kw):
        if cmd == '-':
            statements = parse(self.stdin.read())
        elif cmd.startswith(('./', '/')):
            with open(cmd, 'r') as input_file:
                statements = parse(input_file.read())
        else:
            statements = parse(cmd)

        for line in Executor(statements):
            self.stdout.write(u'{}\n'.format(line))
            r = line()
            self.stdout.write(u'{}\n'.format(r))
            if stop_at_exception and line.failed:
                break
