import collections
import enum
import logging

logger = logging.getLogger(__name__)


class PathSpecMagic(enum.IntFlag):
    """
    Magic signature


    """
    TOP = 1 << 0
    LITERAL = 1 << 2
    GLOB = 1 << 3
    ICASE = 1 << 4
    EXCLUDE = 1 << 5
    ATTR = 1 << 6

    NONE = 0
    ALL = TOP | LITERAL | GLOB | ICASE | EXCLUDE | ATTR


Rule = collections.namedtuple('Rule', ['magic', 'pattern'])


class PathSpec:
    def __init__(self, rules):
        self.rules = rules

    @classmethod
    def parse(cls, rule_strings):
        rules = cls._parse(rule_strings)
        return cls(rules)

    @classmethod
    def _parse(cls, rule_strings):
        rules = []
        for idx, rule_string in enumerate(rule_strings):
            if not rule_string:
                raise ValueError('Empty string found in the {}th rule'.format(idx))

            rules.append(cls._parse_rule(rule_string))

        return rules

    @classmethod
    def _parse_rule(cls, rule):
        if rule.startswith(':'):
            if rule.startswith(':('):
                magic, pattern = cls._parse_rule_long(rule)
            else:
                magic, pattern = cls._parse_rule_short(rule)

            if PathSpecMagic.GLOB in magic and PathSpecMagic.LITERAL in magic:
                raise ValueError('glob magic and literal magic are mutually exclusive')
        else:
            magic = PathSpecMagic.NONE
            pattern = rule

        return magic, pattern

    @classmethod
    def _parse_rule_long(cls, rule):
        assert rule.startswith(':(')

        heading, sep, trailing = rule[2:].partition(')')

        if not sep:
            raise ValueError('Illegal magic signature for {}'.format(rule))

        magic = 0

        for item in heading.split(','):
            if item == 'top':
                magic |= PathSpecMagic.TOP
            elif item == 'literal':
                magic |= PathSpecMagic.LITERAL
            elif item == 'glob':
                magic |= PathSpecMagic.GLOB
            elif item == 'icase':
                magic |= PathSpecMagic.ICASE
            elif item == 'exclude':
                magic |= PathSpecMagic.EXCLUDE
            elif item.startswith('attr:'):
                magic |= PathSpecMagic.ATTR
                raise ValueError('attr magic is not supported')
            else:
                raise ValueError('Unknown magic signature: {}'.format(item))

        return magic, trailing

    @classmethod
    def _parse_rule_short(cls, rule):
        assert rule.startswith(':')

        idx = 0
        magic = 0

        for (idx, ch) in enumerate(rule):
            if idx == 0:
                continue
            if ch == '/':
                magic |= PathSpecMagic.TOP
            elif ch in '!^':
                magic |= PathSpecMagic.EXCLUDE
            else:
                if ch == ':':
                    idx = idx + 1
                break
        else:
            # reach the end of the pattern without break
            return magic, rule[idx + 1:]

        return magic, rule[idx:]
