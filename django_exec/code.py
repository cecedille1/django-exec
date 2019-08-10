import ast
import sys
import collections
import traceback

from django_exec.parse import parse


class Line(collections.namedtuple('Line', ['ast', 'original'])):
    @classmethod
    def build(cls, original):
        line = original.strip()

        if line.startswith('_ '):
            _, line = line.split(' ', 1)
            line = '{{x: y for x, y in vars({}).items() if not x.startswith("__")}}'.format(line)
        elif line.startswith('__ '):
            _, line = line.split(' ', 1)
            line = 'vars({})'.format(line)

        try:
            parsed = ast.parse(line, mode='eval')
        except SyntaxError:
            pass
        else:
            return Expression(parsed, original)

        try:
            parsed = ast.parse(line)
        except SyntaxError as e:
            return MisformattedStatement(e, original)

        return Statement(parsed, original)

    def __str__(self):
        return '>>> {}'.format(self.original)


class Statement(Line):
    def __call__(self, globals_, locals_):
        previous = locals_.copy()
        exec(self.code, globals_, locals_)
        return self._find_changes(previous, locals_)

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
        return compile(self.ast, '<string>', 'exec')


class Expression(Line):
    def __call__(self, globals_, locals_):
        return Evaluation(self, eval(self.code, globals_, locals_))

    @property
    def code(self):
        return compile(self.ast, self.original, 'eval')


class MisformattedStatement(Line):
    def __call__(self, globals_, locals_):
        raise self.ast

    def __str__(self):
        original = super().__str__()
        return '{}\n{}'.format(original, self.ast)


class Failed(collections.namedtuple('Failed', ['line', 'error'])):
    def __str__(self):
        return str(self.error)


class Success(collections.namedtuple('Success', ['line', 'additions', 'changes'])):
    def __str__(self):
        buff = []
        for k, v in sorted(self.additions.items()):
            buff.append('    {}: {!r}'.format(k, v))
        for k, (v1, v2) in sorted(self.changes.items()):
            buff.append('    {}: {!r} -> {!r}'.format(k, v1, v2))
        return '\n'.join(buff)


class Evaluation(collections.namedtuple('Evaluation', ['line', 'evaluation'])):
    @property
    def evaluation_repr(self):
        if isinstance(self.evaluation, dict):
            return '{\n%s    }' % ''.join('        {key!r}: {value!r},\n'.format(key, value) for key, value in self.evaluation.items())
        return repr(self.evaluation)

    def __str__(self):
        return '    {}'.format(self.evaluation_repr)


class Executor:
    """
    A step by step python code executor.

    It executes line by line a line of instructions separated by a ; and yields
    a detailled version of the results of the operation.
    """

    def __init__(self, statements):
        self._locals = {}
        self._globals = globals()
        self._globals['__name__'] = None
        self._code = [Line.build(line) for line in statements]

    def __iter__(self):
        for code in self._code:
            yield ExecutionStep(code, self._globals, self._locals)

    def __call__(self, stdout=None, stop_at_exception=False):
        stdout = stdout or sys.stdout
        for line in self:
            stdout.write('{}\n'.format(line))
            r = line()
            stdout.write('{}\n'.format(r))
            if stop_at_exception and line.failed:
                break

    @classmethod
    def parse(cls, cmd, stdin=None):
        stdin = stdin or sys.stdin
        statements = parse(cmd, stdin)
        return cls(statements)


class ExecutionStep:
    def __init__(self, code, globals_, locals_):
        self.code = code
        self.globals_ = globals_
        self.locals_ = locals_
        self.failed = None

    def __str__(self):
        return str(self.code)

    def __call__(self):
        try:
            value = self.code(self.globals_, self.locals_)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = ''.join(traceback.format_tb(exc_traceback) +
                         ['   ', self.code.original, '\n'] +
                         traceback.format_exception_only(exc_type, exc_value))
            self.failed = True
            return Failed(self.code, tb)
        self.failed = False
        return value
