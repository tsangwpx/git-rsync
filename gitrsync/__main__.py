import argparse
import logging
import os
import subprocess
from collections import OrderedDict
from types import SimpleNamespace

from .utils import cached_result
from .gitutils import rev_parse, to_bool, Configuration, ChainConfiguration

logger = logging.getLogger(__name__)

PROGRAM_NAME = 'git rsync'
GIT_BIN = '/usr/bin/git'
GIT_CONFIG_SECTION = 'rsync'
RSYNC_BIN = 'rsync'


@cached_result
def get_repo_info():
    repo_info = SimpleNamespace()

    option_inside_worktree = '--is-inside-work-tree'

    results = rev_parse((
        '--git-dir',
        '--git-common-dir',
        '--show-toplevel',
        '--show-prefix',
        option_inside_worktree
    ))

    repo_info.git_dir = results[0]
    # --git-common-dir is returned when git does not support it
    repo_info.git_common_dir = results[1] if results[1] != '--git-common-dir' else results
    repo_info.toplevel = results[2]
    repo_info.prefix = results[3]

    def workaround_098aa867():
        if not (repo_info.prefix and os.path.join(repo_info.prefix, '.git') == repo_info.git_common_dir):
            # Seem no problem found
            return

        # GIT_COMMON_DIR may be incorrectly set inside subdirectories of the master work-tree
        # git v2.11.0 is affected and included in Debian stretch
        # See: https://github.com/git/git/commit/098aa867626ef2444ef14a92b428a6ca26d83e60
        logger.debug('Applying workaround 098aa867')
        repo_info.git_common_dir = repo_info.git_dir

    workaround_098aa867()

    logger.debug('repo_info(): git_dir=%s, git_common_dir=%s, toplevel=%s, prefix=%s', repo_info.git_dir,
                 repo_info.git_common_dir, repo_info.toplevel, repo_info.prefix)

    return repo_info


@cached_result
def get_config():
    repo_info = get_repo_info()

    config = Configuration()

    if repo_info.git_dir != repo_info.git_common_dir:
        # GIT_DIR should point to branch root in worktrees
        if 'worktrees' not in repo_info.git_dir:
            raise AssertionError('unexpected path component format in GIT_DIR')

        filepath = os.path.join(repo_info.git_dir, 'git-rsync')
        top_config = Configuration(file=filepath)

        config = ChainConfiguration((top_config, config))

    return config


def create_parser():
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME)
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--version', action='store_true', help='Show version')

    subparsers = parser.add_subparsers(dest='command')

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('name', help='remote name')
    add_parser.add_argument('url', help='remote URL')

    remove_parser = subparsers.add_parser('remove')
    remove_parser.add_argument('name', help='remote name')

    list_parser = subparsers.add_parser('list')

    transfer_parser = argparse.ArgumentParser(add_help=False)
    transfer_parser.add_argument('-v', '--verbose', action='count', default=0)
    transfer_parser.add_argument('-n', '--dry-run', action='store_true', help='Dry run only')
    transfer_parser.add_argument('--include-git-dir', action='store_true', default=False,
                                 help='Include .git directory in transfer')
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
    log_level = None

    if ns.verbose >= 2:
        log_level = logging.DEBUG
    elif ns.verbose >= 1:
        log_level = logging.INFO

    if log_level is not None:
        # Remove existing handlers from the root logger
        # See https://stackoverflow.com/a/13839732/1692260
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)

        logging.basicConfig(level=log_level)

    command = ns.command

    logger.debug(ns)

    if ns.version:
        do_version(ns)
    elif command == 'add':
        do_add(ns)
    elif command == 'remove':
        do_remove(ns)
    elif command == 'list':
        do_list(ns)
    elif command == 'download' or command == 'upload':
        do_transfer(ns)


def do_version(ns):
    from . import __version__
    print('%s' % (__version__,))


def do_add(ns):
    (name, url) = (ns.name, ns.url)

    if not name:
        raise RuntimeError('No name is specified')
    if not url:
        raise RuntimeError('No URL is specified')

    logger.debug('Add host %s with URL %s', ns.name, ns.url)

    config = get_config()
    config.put('%s.%s.url' % (GIT_CONFIG_SECTION, name), url)


def do_remove(ns):
    name = ns.name

    if not name:
        raise ValueError('No name is specified')

    logger.debug('Remove host %', ns.name)

    config = get_config()
    config.remove_section('%s.%s' % (GIT_CONFIG_SECTION, name))


def do_list(ns):
    import re

    config = get_config()

    pattern = r'%s\.(.+)\.url' % (GIT_CONFIG_SECTION,)
    data = config.get_regexp(pattern)

    urls = OrderedDict()

    for key, url in data:
        match = re.match(pattern, key)

        if match:
            host = match.group(1)
            urls[host] = url

    if urls:
        column_length = max(len(s) for s in urls.keys())

        fmt = r'{: <%d} {}' % column_length

        for name, url in urls.items():
            print(fmt.format(name, url))


def do_transfer(ns):
    from gitrsync.pathspec import PathSpec
    from gitrsync.translator import Translator

    command = ns.command
    dry_run = ns.dry_run
    name = ns.name
    pathspec = ns.pathspec

    assert command in ('upload', 'download')

    config = get_config()
    url = config.get('%s.%s.url' % (GIT_CONFIG_SECTION, name))

    if not url:
        raise RuntimeError('Unknown remote name {}'.format(name))

    repo_info = get_repo_info()

    rsync_cmds = [
        RSYNC_BIN,
        '-azP',
    ]
    rsync_input = None

    if dry_run:
        rsync_cmds.append('-n')

    if ns.verbose:
        rsync_cmds.append('-' + 'v' * ns.verbose)

    if not ns.include_git_dir:
        rsync_cmds.append('--exclude=.git/')

    if pathspec:
        prefix = repo_info.prefix

        ps = PathSpec.parse(pathspec)
        translator = Translator(prefix, ps)
        translator.translate()
        filters = translator.filters

        logger.debug('filter %s', filters)
        rsync_cmds.append('--filter=merge -')
        rsync_input = '\n'.join(filters)

        prefix = translator.common_prefix
    else:
        prefix = ''

    path = os.path.join(url, prefix)

    if command == 'upload':
        direction = ('.', path)
    else:
        direction = (path + '/' if path else './', '.')

    logger.info('Transfer files from %s to %s', *direction)

    rsync_cmds.extend(direction)

    toplevel = repo_info.toplevel
    cwd = os.path.join(toplevel, prefix)

    logger.debug('command=%s,remotepath=%s', command, path)
    logger.debug('rsync=%s', rsync_cmds)
    logger.debug('cwd=%s', cwd)

    subprocess.run(rsync_cmds, cwd=os.path.join(toplevel, prefix), input=rsync_input, universal_newlines=True)


if __name__ == '__main__':
    main()
