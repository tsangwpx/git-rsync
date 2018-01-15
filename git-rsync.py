#!/usr/bin/python3

import argparse
import sys
import subprocess
import os.path

PROGRAM_NAME = 'git rsync'
GIT_BIN = '/usr/bin/git'
GIT_CONFIG_SECTION = 'rsync'
RSYNC_BIN = '/usr/bin/rsync'


def debug(msg):
    if not debug.verbose:
        return

    msg = '[debug] ' + str(msg)

    logger = debug.logger
    if not logger:
        import logging
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        debug.logger = logger

    logger.debug(msg)


debug.verbose = 0
debug.logger = None


def create_parser():
    parser = argparse.ArgumentParser(prog='git rsync')
    parser.add_argument('-v', '--verbose', action='count', default=0)

    subparsers = parser.add_subparsers(dest='command')

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('name', help='remote name')
    add_parser.add_argument('url', help='remote URL')

    remove_parser = subparsers.add_parser('remove')
    remove_parser.add_argument('name', help='remote name')

    list_parser = subparsers.add_parser('list')

    transfer_parser = argparse.ArgumentParser(add_help=False)
    transfer_parser.add_argument('-n', '--dry-run', action='store_true', help='Dry run only')
    transfer_parser.add_argument('name', help='remote name')
    transfer_parser.add_argument('pathspec', nargs='*', help='file paths in interest')
    subparsers.add_parser('download', parents=[transfer_parser])
    subparsers.add_parser('upload', parents=[transfer_parser])

    return parser


def parse():
    parser = create_parser()
    ns = parser.parse_args()
    return ns


def main():
    ns = parse()

    debug.verbose = ns.verbose
    command = ns.command

    debug(ns)

    if command == 'add':
        do_add(ns)
    elif command == 'remove':
        do_remove(ns)
    elif command == 'list':
        do_list(ns)
    elif command == 'download' or command == 'upload':
        do_transfer(ns)


def do_add(ns):
    (name, url) = (ns.name, ns.url)

    if not name:
        raise RuntimeError('No name is specified')
    if not url:
        raise RuntimeError('No URL is specified')

    config_set('{}.{}.url'.format(GIT_CONFIG_SECTION, name), url)

    if ns.verbose:
        debug('{} is added with URL {}'.format(name, url))


def do_remove(ns):
    name = ns.name

    if not name:
        raise ValueError('No name is specified')

    config_remove_section('{}.{}'.format(GIT_CONFIG_SECTION, name))

    if ns.verbose:
        debug('{} is removed'.format(name))


def do_list(ns):
    import re

    pattern = "{}\\.(.+)\\.url".format(GIT_CONFIG_SECTION)
    data = config_get_regexp(pattern)

    name_length = 0
    urls = []

    for key, url in data:
        match = re.match(pattern, key)

        if match:
            name = match.group(1)
            name_length = max(name_length, len(name))
            urls.append((name, url))

    if name_length > 20:
        name_length = 20

    fmt = "{: <" + str(name_length) + "}  {}"
    for name, url in urls:
        print(fmt.format(name, url))


def do_transfer(ns):
    command = ns.command
    dry_run = ns.dry_run
    name = ns.name
    pathspec = ns.pathspec

    assert command in ('upload', 'download')

    url = config_get('{}.{}.url'.format(GIT_CONFIG_SECTION, name))

    if not url:
        raise RuntimeError('Unknown remote name {}'.format(name))

    prefix = git_rev_parse('show-prefix')

    rsync_cmds = [
        RSYNC_BIN,
        '-azP',
    ]

    if dry_run:
        rsync_cmds.append('-n')

    if ns.verbose:
        rsync_cmds.append('-' + 'v' * ns.verbose)

    if pathspec:
        for item in pathspec:
            if item and item[0] == ':':
                raise ValueError('Path starting with colon: {}'.format(item))
            if os.path.isabs(item):
                raise ValueError('Absolute path is not supported')
            if '..' in item:
                raise ValueError('No support for .. currently')

            rsync_cmds.append('--include=' + item)

        rsync_cmds.append('--exclude=*')
        print(pathspec)
    else:
        debug('Rsync the file in the directory {}'.format(prefix))

    path = os.path.join(url, prefix)

    if command == 'upload':
        direction = ('.', path)
    else:
        direction = (path, '.')

    rsync_cmds.extend(direction)

    if ns.verbose:
        debug('command={}\nremotepath={}'.format(command, path))
        debug('rsync={}'.format(rsync_cmds))

    subprocess.run(rsync_cmds)


def git_rev_parse(command):
    if command in ('show-toplevel', 'show-cdup', 'show-prefix'):
        return subprocess.check_output([
            GIT_BIN,
            'rev-parse',
            '--' + command
        ], universal_newlines=True, encoding='UTF-8').rstrip('\r\n')
    else:
        raise ValueError('Unknown command {}'.format(command))


def config_get(key, default=None):
    process = subprocess.run([
        GIT_BIN,
        'config',
        '--get',
        key,
    ], stdout=subprocess.PIPE, universal_newlines=True, encoding='UTF-8')

    if process.returncode == 1:
        return default
    elif process.returncode:
        raise RuntimeError('Unknown return code {}'.format(process.returncode))

    return process.stdout.rstrip('\r\n')


def config_get_regexp(regexp):
    import re
    process = subprocess.run([
        GIT_BIN,
        'config',
        '--get-regexp',
        regexp
    ], stdout=subprocess.PIPE, universal_newlines=True, encoding='UTF-8')

    if process.returncode == 1:
        return []
    elif process.returncode:
        raise RuntimeError('Unknown return code {}'.format(process.returncode))

    return list(re.split('\s+', s, 2) for s in process.stdout.splitlines() if s)


def config_set(key, value):
    subprocess.check_call([
        GIT_BIN,
        'config',
        key,
        value
    ])


def config_remove_section(key):
    subprocess.check_call([
        GIT_BIN,
        'config',
        '--remove-section',
        key
    ])


if __name__ == '__main__':
    main()
