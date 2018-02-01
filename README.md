# django-exec

Django-exec provides a management command `exec` that use arbitrary python
code, juste like the `exec` function in standard python.

## Installation

Add `django_exec` in your `INSTALLED_APPS`.

## Usage

    $ ./manage.py exec '1 + 1'
    >>> 1 + 1
    2
