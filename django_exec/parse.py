# -*- coding: utf-8 -*-

import sys
from django.utils.six import text_type


def parse(value, stdin=sys.stdin):
    if value == '-':
        return _parse(stdin.read())
    elif value.startswith(('./', '/')):
        with open(value, 'r') as input_file:
            return _parse(input_file.read())
    return _parse(value)


def _parse(input):
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
