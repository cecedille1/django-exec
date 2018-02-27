# -*- coding: utf-8 -*-

import pytest
import sys
import io
import os.path
from django.utils import six

import importlib
# exec is a py2 syntax error
exec_ = importlib.import_module('django_exec.management.commands.exec')
Command = exec_.Command


def test_exec_help():
    c = Command()
    with pytest.raises(SystemExit) as e:
        c.run_from_argv(['./manage.py', 'exec'])
    assert e.value.args == (2, )


@pytest.fixture
def stdout():
    if six.PY2:
        return io.BytesIO()
    else:
        return io.StringIO()


@pytest.fixture
def command(stdout):
    stdin = io.StringIO(u'1 + 1')
    return Command(stdout=stdout, stdin=stdin)


def test_exec(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', '1 + 1'])
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_stdin(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', '-'])
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_stdin_bytes(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', '-'])
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_file(command, stdout):
    path = os.path.join(os.path.dirname(__file__), 'data', 'input')
    command.run_from_argv(['./manage.py', 'exec', path])
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_file_multiline(command, stdout):
    path = os.path.join(os.path.dirname(__file__), 'data', 'multiline')
    command.run_from_argv(['./manage.py', 'exec', path])
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n>>> 1 + 1\n    2\n'


def test_exec_assign(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', 'a = 1'])
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n'


def test_exec_print(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', '__import__("sys").stdout.write("1\\n")'])
    assert stdout.getvalue() == '>>> __import__("sys").stdout.write("1\\n")\n    None\n'


def test_exec_import(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', 'from os import SEEK_CUR'])
    assert stdout.getvalue() == '>>> from os import SEEK_CUR\n    SEEK_CUR: 1\n'


def test_exec_keep_context(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', 'a = 1;a += 1'])
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n>>> a += 1\n    a: 1 -> 2\n'


def test_exception(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', 'b'])
    output = stdout.getvalue()
    assert '''NameError: name 'b' is not defined''' in output
    assert '''File "b", line 1, in <module>''' in output


def test_syntax_error(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', 'b -'])
    output = stdout.getvalue()
    assert '''SyntaxError: invalid syntax''' in output


def test_print_dict(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', 'dict(a=1, b=2)'])
    if sys.version_info.major == 3 and sys.version_info.minor < 6:
        pytest.xfail('Inconsistent dict hashing until python 3.6')
    assert stdout.getvalue() == ">>> dict(a=1, b=2)\n    {\n        'a': 1,\n        'b': 2,\n    }\n"


def test_class_decl(command, stdout):
    command.run_from_argv(['./manage.py', 'exec', 'class A(object):pass'])
    assert stdout.getvalue() == ">>> class A(object):pass\n    A: <class 'django_exec.management.commands.exec.A'>\n"
