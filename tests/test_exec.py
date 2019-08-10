# -*- coding: utf-8 -*-

import pytest
import sys
import io
import os.path
from django.utils import six

import importlib
from django.core.management import call_command, CommandError


def test_exec_help():
    with pytest.raises(CommandError) as e:
        call_command('exec')


@pytest.fixture
def stdout():
    return io.StringIO()


def test_exec(stdout):
    call_command('exec', '1 + 1', stdout=stdout)
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_stdin(monkeypatch, stdout):
    monkeypatch.setattr('sys.stdin', io.StringIO('1 + 1'))
    call_command('exec', '-', stdout=stdout)
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_file(stdout):
    path = os.path.join(os.path.dirname(__file__), 'data', 'input')
    call_command('exec', path, stdout=stdout)
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_file_multiline(stdout):
    path = os.path.join(os.path.dirname(__file__), 'data', 'multiline')
    call_command('exec', path, stdout=stdout)
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n>>> 1 + 1\n    2\n'


def test_exec_assign(stdout):
    call_command('exec', 'a = 1', stdout=stdout)
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n'


def test_exec_print(stdout):
    call_command( 'exec', '__import__("sys").stdout.write("1\\n")', stdout=stdout)
    assert stdout.getvalue() == '>>> __import__("sys").stdout.write("1\\n")\n    None\n'


def test_exec_import(stdout):
    call_command('exec', 'from os import SEEK_CUR', stdout=stdout)
    assert stdout.getvalue() == '>>> from os import SEEK_CUR\n    SEEK_CUR: 1\n'


def test_exec_keep_context(stdout):
    call_command('exec', 'a = 1;a += 1', stdout=stdout)
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n>>> a += 1\n    a: 1 -> 2\n'


def test_exception(stdout):
    call_command('exec', 'b', stdout=stdout)
    output = stdout.getvalue()
    assert '''NameError: name 'b' is not defined''' in output
    assert '''File "b", line 1, in <module>''' in output


def test_syntax_error(stdout):
    call_command('exec', 'b -', stdout=stdout)
    output = stdout.getvalue()
    assert '''SyntaxError: invalid syntax''' in output


def test_print_dict(stdout):
    call_command('exec', 'dict(a=1, b=2)', stdout=stdout)
    if sys.version_info.major == 3 and sys.version_info.minor < 6:
        pytest.xfail('Inconsistent dict hashing until python 3.6')
    assert stdout.getvalue() == ">>> dict(a=1, b=2)\n    {\n        'a': 1,\n        'b': 2,\n    }\n"


def test_class_decl(stdout):
    call_command('exec', 'class A(object):pass', stdout=stdout)
    assert stdout.getvalue() == ">>> class A(object):pass\n    A: <class 'A'>\n"
