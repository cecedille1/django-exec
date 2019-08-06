# -*- coding: utf-8 -*-

import sys

from django.core.management import BaseCommand
from django_exec.code import Executor
from django_exec.__main__ import augment_parser


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
        super().add_arguments(parser)
        augment_parser(parser)

    def handle(self, cmd, stop_at_exception=False, **kw):
        executor = Executor.parse(cmd, stdin=self.stdin)
        executor(stdout=self.stdout, stop_at_exception=stop_at_exception)
