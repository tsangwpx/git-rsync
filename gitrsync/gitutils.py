import logging
import subprocess

logger = logging.getLogger(__name__)

GIT_BIN = '/usr/bin/git'


def _run_command(*args, **kwargs):
    if 'universal_newlines' not in kwargs:
        kwargs['universal_newlines'] = True

    logger.debug('Executing %s', args[0])

    return subprocess.check_output(*args, **kwargs).rstrip('\r\n')


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
            return (line.split(maxsplit=2) for line in output.splitlines())
        except subprocess.CalledProcessError as err:
            if err.returncode == 1:
                return iter(())
            raise
