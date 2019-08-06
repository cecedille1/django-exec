# -*- coding: utf-8 -*-

from argparse import ArgumentParser

from django_exec.code import Executor


def augment_parser(parser: ArgumentParser) -> ArgumentParser:
    parser.add_argument('cmd')
    parser.add_argument(
        '-c',
        '--contine',
        dest='stop_at_exception',
        help='Continue when an exception is raised',
        action='store_false',
        default=True,
    )
    return parser


def main():
    parser = ArgumentParser()
    augment_parser(parser)
    options = parser.parse_args()
    executor = Executor.parse(options.cmd)
    executor(stop_at_exception=options.stop_at_exception)


if __name__ == '__main__':
    main()
