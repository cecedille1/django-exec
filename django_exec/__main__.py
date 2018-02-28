# -*- coding: utf-8 -*-

import sys
import argparse

from django_exec.parse import parse
from django_exec.code import Executor


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd')
    parser.add_argument('-c',
                        '--contine',
                        dest='stop_at_exception',
                        help='Continue when an exception is raised',
                        action='store_false',
                        default=True,
                        )
    return parser


def main():
    argparser = get_parser()
    options = argparser.parse_args()

    statements = parse(options.cmd)
    for line in Executor(statements):
        sys.stdout.write(u'{}\n'.format(line))
        r = line()
        sys.stdout.write(u'{}\n'.format(r))
        if options.stop_at_exception and line.failed:
            break


if __name__ == '__main__':
    main()
