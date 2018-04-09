import itertools
import logging
import subprocess

logger = logging.getLogger(__name__)

GIT_BIN = '/usr/bin/git'


def to_bool(value):
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        value = value.lower()

        if value in ('true', 'yes', 'on', '1'):
            return True
        elif value in ('false', 'no', 'off', '0', ''):
            return False
        else:
            raise ValueError('Unknown conversion of str value: %s' % (value,))
    elif isinstance(value, int):
        return bool(value)
    else:
        raise TypeError('Unknown type %s' % (type(value),))


def _run_command(*args, remove_trailing_newline=True, **kwargs):
    if 'universal_newlines' not in kwargs:
        kwargs['universal_newlines'] = True

    logger.debug('Executing %s', args[0])

    output = subprocess.check_output(*args, **kwargs)
    if remove_trailing_newline and output and output[-1] == '\n':
        return output[:-1]
    return output


def rev_parse(options):
    args = [
            GIT_BIN,
            'rev-parse',
    ]

    args.extend(options)

    return _run_command(args).splitlines()


def git_dir():
    args = [
        GIT_BIN,
        'rev-parse',
        '--git-dir',
    ]

    return _run_command(args)


def git_common_dir():
    args = [
        GIT_BIN,
        'rev-parse',
        '--git-common-dir',
    ]

    return _run_command(args)


class BaseConfiguration:
    def get(self, key, default=None, get_bool=False, get_int=False):
        raise NotImplementedError()

    def get_bool(self, key, default=None):
        return self.get(key, default, get_bool=True)

    def get_int(self, key, default=None):
        return self.get(key, default, get_int=True)

    def get_regexp(self, key, get_bool=False, get_int=False):
        raise NotImplementedError()

    def get_all(self, key, get_bool=False, get_int=False):
        return NotImplementedError()

    def put(self, key, value):
        return NotImplementedError()

    def unset(self, key):
        raise NotImplementedError()

    def unset_all(self, key):
        raise NotImplementedError()

    def remove_section(self, name):
        raise NotImplementedError()

    @staticmethod
    def _cast_type(output, get_bool, get_int):
        if get_bool or get_int:
            if output in ('true', 'false'):
                return output == 'true'
            else:
                return int(output)

        return output


class Configuration(BaseConfiguration):
    def __init__(self, file=None):
        self._file = file

    def _build_args_prefix(self):
        args = [
            GIT_BIN,
            'config',
        ]

        if self._file:
            args.extend(('--file', self._file))

        return args

    def _build_args_type(self, args, output_bool, output_int):
        if output_bool and output_int:
            args.append('--boot-or-int')
        elif output_bool:
            args.append('--boot')
        elif output_int:
            args.append('--int')

        return args

    def get(self, key, default=None, get_bool=False, get_int=False):
        args = self._build_args_prefix()
        args = self._build_args_type(args, get_bool, get_int)

        args.extend(('--get', key))

        try:
            output = _run_command(args)
            return self._cast_type(output, get_bool, get_int)
        except subprocess.CalledProcessError as error:
            if error.returncode == 1:
                return default
            raise

    def get_regexp(self, pattern, get_bool=False, get_int=False):
        args = self._build_args_prefix()
        args = self._build_args_type(args, get_bool, get_int)

        args.extend(('--get-regexp', pattern))

        try:
            output = _run_command(args)
            return list(line.split(maxsplit=2) for line in output.splitlines())
        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                return []
            raise

    def get_all(self, key, get_bool=False, get_int=False):
        args = self._build_args_prefix()
        args = self._build_args_type(args, get_bool, get_int)

        args.extend(('--get-all', key))

        try:
            output = _run_command(args)
            return output.splitlines()
        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                return []
            raise

    def put(self, key, value):
        args = self._build_args_prefix()
        args.extend((key, value))

        _run_command(args)

    def unset(self, key):
        args = self._build_args_prefix()
        args.extend(('--unset', key))

        try:
            _run_command(args)
            return True
        except subprocess.ChildProcessError as err:
            if err.returncode == 5:
                return False
            raise

    def unset_all(self, key):
        args = self._build_args_prefix()
        args.extend(('--unset-all', key))

        try:
            _run_command(args)
            return True
        except subprocess.CalledProcessError as err:
            if err.returncode == 5:
                return False
            raise

    def remove_section(self, name):
        args = self._build_args_prefix()
        args.extend(('--remove-section', name))

        try:
            _run_command(args)
            return True
        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                return False
            raise


class ChainConfiguration(BaseConfiguration):
    """
    Chained configuration

    """

    def __init__(self, configs):
        configs = list(configs)

        if not configs or any(not isinstance(conf, BaseConfiguration) for conf in configs):
            raise TypeError()

        self.configs = configs

    def get(self, key, default=None, get_bool=False, get_int=False):
        for conf in self.configs:
            result = conf.get(key, None, get_bool=get_bool, get_int=get_int)

            if result is not None:
                return result

        return default

    def get_regexp(self, key, get_bool=False, get_int=False):
        iterables = (conf.get_regexp(key, get_bool=get_bool, get_int=get_int) for conf in reversed(self.configs))
        return itertools.chain.from_iterable(iterables)

    def put(self, key, value):
        return self.configs[0].put(key, value)
