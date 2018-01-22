import itertools
import logging
import operator
from pathlib import PurePosixPath

from .pathspec import PathSpecMagic

logger = logging.getLogger(__name__)

UNSUPPORTED_MAGIC = PathSpecMagic.ATTR \
                    | PathSpecMagic.TOP \
                    | PathSpecMagic.LITERAL \
                    | PathSpecMagic.GLOB \
                    | PathSpecMagic.ICASE


class Rule:
    def __init__(self, magic, pattern):
        self.magic = magic
        self.pattern = pattern
        self.parts = PurePosixPath(pattern).parts
        self.trailing_slash = pattern[-1] in '/\\'
        self.includes = None
        self.excludes = None

    def __str__(self):
        return '%s %s' % (self.magic, self.pattern)


class Translator:
    """
    Algorithm:
    1. Find the long prefix to the root of the repository so the sender can save some time in finding all files
        Example 1:
            cwd: / the root of repository
            pathspec: apple/orange apple/cherry/*
            prefix: /apple/
        Example 2:
            cwd: apple
            pathspec: orange cherry/*
            prefix: /apple/
        Example 3:
            cwd: apple/orange
            pathspec: . ../cherry
            prefix: /apple
    2. No pathspec, match everthing starting from the repo root
    3. Empty pathspec is invalid, it is same as "."
    """

    def __init__(self, prefix, ps):
        self._translated = False
        self._filters = None
        self.rules = None
        self.prefix = prefix
        self.prefix_parts = PurePosixPath(prefix).parts
        self.pathspec = ps
        self.common_parts = None
        self.common_prefix = None
        self._all_excludes = None

    def translate(self):
        if not self._translated:
            self._translate()

    def _translate(self):
        logger.debug('prefix=%s, parts=%s', self.prefix, self.prefix_parts)

        self.rules = list(Rule(magic, pattern) for magic, pattern in self.pathspec.rules)
        self._all_excludes = all(PathSpecMagic.EXCLUDE in rule.magic for rule in self.rules)

        # Normalize and convert rule pattern into parts
        for rule in self.rules:
            bad_magic = UNSUPPORTED_MAGIC & rule.magic

            if bad_magic:
                raise ValueError('{} is not suported'.format(bad_magic))

            try:
                rule.parts = self._abs_parts(rule.parts)
            except ValueError as e:
                raise ValueError('Illegal pathspec {}'.format(rule.pattern)) from e

        self.common_parts = self._find_common_parts()
        self.common_prefix = '/'.join(self.common_parts)
        common_length = len(self.common_parts)

        logger.debug('Common parts: %s', self.common_parts)

        # In this loop, include and exclude filters of each rule are created respectively
        for rule in self.rules:
            # Remove common parts
            rule.parts = rule.parts[common_length:]

            logger.debug('Rule: %s %s => %s', rule.magic, rule.pattern, rule.parts)

            rule.includes = []
            rule.excludes = []

            if not rule.parts:
                if PathSpecMagic.EXCLUDE in rule.magic:
                    rule.excludes.append('***')
                else:
                    rule.includes.append('***')

                continue

            rsync_parts = rule.parts

            if PathSpecMagic.GLOB not in rule.magic:
                rsync_parts = tuple(s.replace('*', '**') for s in rule.parts)

            # First, handle the directory prefix
            slashed_parts = map(lambda s: s + '/', rsync_parts[:-1])
            rule.includes.extend(itertools.accumulate(slashed_parts, operator.add))

            final_path = '/'.join(rsync_parts)
            if PathSpecMagic.EXCLUDE in rule.magic:
                rule.excludes.append(final_path + '/***')
                if not rule.trailing_slash:
                    rule.excludes.append(final_path)
            else:
                rule.includes.append(final_path + '/***')
                if not rule.trailing_slash:
                    rule.includes.append(final_path)

        self._translated = True

    def _abs_parts(self, parts):
        abs_parts = list(self.prefix_parts)

        for part in parts:
            if part == '..':
                if not abs_parts:
                    raise ValueError('Out of repository')
                abs_parts.pop()
            else:
                abs_parts.append(part)

        return tuple(abs_parts)

    def _find_common_parts(self):
        common_parts = self.prefix_parts if self._all_excludes else None

        for rule in self.rules:
            parts = rule.parts if rule.trailing_slash else rule.parts[:-1]

            if PathSpecMagic.LITERAL in rule.magic:
                simple_parts = parts
            else:
                simple_parts = tuple(itertools.takewhile(lambda part: all(ch not in '*[?' for ch in part), parts))

            if common_parts is None or not simple_parts:
                common_parts = simple_parts
            else:
                idx = 0
                for idx, (left, right) in enumerate(zip(common_parts, simple_parts)):
                    if left == right:
                        continue
                    common_parts = common_parts[:idx]
                    break
                else:
                    common_parts = common_parts[:idx + 1]

        return common_parts if common_parts else []

    @property
    def filters(self):
        self.translate()

        if self._filters is None:
            self._translate()

            iterables = [
                map(lambda s: '- ' + s, itertools.chain.from_iterable(rule.excludes for rule in self.rules)),
                map(lambda s: '+ ' + s, itertools.chain.from_iterable(rule.includes for rule in self.rules)),
            ]

            if self._all_excludes:
                # Include everything only if all rule are with exclude magic
                iterables.append(('+ ***',))
            else:
                # Exclude everything else
                iterables.append(('- *',))

            self._filters = tuple(itertools.chain.from_iterable(iterables))

        return self._filters


__all__ = ['Translator']
