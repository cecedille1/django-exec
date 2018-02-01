# -*- coding: utf-8 -*-

import pytest
import io
import os.path

from django_exec.management.commands.exec import Command


def test_exec_help():
    c = Command()
    with pytest.raises(SystemExit) as e:
        c.run_from_argv(['./manage.py', 'exec'])
    assert e.value.args == (2, )


def test_exec():
    stdout = io.StringIO()
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', '1 + 1'])
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_stdin():
    stdout = io.StringIO()
    stdin = io.StringIO('1 + 1')
    c = Command(stdout=stdout, stdin=stdin)
    c.run_from_argv(['./manage.py', 'exec', '-'])
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_stdin_bytes():
    stdout = io.StringIO()
    stdin = io.BytesIO(b'1 + 1')
    c = Command(stdout=stdout, stdin=stdin)
    c.run_from_argv(['./manage.py', 'exec', '-'])
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_file():
    stdout = io.StringIO()
    path = os.path.join(os.path.dirname(__file__), 'data', 'input')
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', path])
    assert stdout.getvalue() == '>>> 1 + 1\n    2\n'


def test_exec_file_multiline():
    stdout = io.StringIO()
    path = os.path.join(os.path.dirname(__file__), 'data', 'multiline')
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', path])
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n>>> 1 + 1\n    2\n'


def test_exec_assign():
    stdout = io.StringIO()
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', 'a = 1'])
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n'


def test_exec_import():
    stdout = io.StringIO()
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', 'from os import SEEK_CUR'])
    assert stdout.getvalue() == '>>> from os import SEEK_CUR\n    SEEK_CUR: 1\n'


def test_exec_keep_context():
    stdout = io.StringIO()
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', 'a = 1;a += 1'])
    assert stdout.getvalue() == '>>> a = 1\n    a: 1\n>>> a += 1\n    a: 1 -> 2\n'


def test_exception():
    stdout = io.StringIO()
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', 'b'])
    output = stdout.getvalue()
    assert '''NameError: name 'b' is not defined''' in output
    assert '''File "b", line 1, in <module>''' in output


def test_syntax_error():
    stdout = io.StringIO()
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', 'b -'])
    output = stdout.getvalue()
    assert '''SyntaxError: invalid syntax''' in output


def test_print_dict():
    stdout = io.StringIO()
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', 'dict(a=1, b=2)'])
    assert stdout.getvalue() == ">>> dict(a=1, b=2)\n    {\n        'a': 1,\n        'b': 2,\n    }\n"


def test_class_decl():
    stdout = io.StringIO()
    c = Command(stdout=stdout)
    c.run_from_argv(['./manage.py', 'exec', 'class A(object):pass'])
    assert stdout.getvalue() == ">>> class A(object):pass\n    A: <class 'django_exec.management.commands.exec.A'>\n"
