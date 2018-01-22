import logging
import unittest

from gitrsync.pathspec import PathSpec
from gitrsync.translator import Translator, logger as t_logger


class TranslatorTest(unittest.TestCase):
    def setUp(self):
        t_logger.setLevel(logging.DEBUG)

    def test_dot(self):
        """
        Test a single dot directory

        """
        self._testTranslator(
            '',
            ('.',),
            '',
            ('+ ***', '- *')
        )

    def test_single_file(self):
        """
        Test a single pathspec without stars
        """
        self._testTranslator(
            '',
            ('docs/README.md',),
            'docs',
            ('+ README.md/***', '+ README.md', '- *')
        )

    def test_file(self):
        """
        Test multiple files without stars
        """
        self._testTranslator(
            '',
            ('README.md', 'HOWTO.md'),
            '',
            ('+ README.md/***', '+ README.md', '+ HOWTO.md/***', '+ HOWTO.md', '- *')
        )

    def test_dir(self):
        """
        pathspec with trailing slash
        """
        self._testTranslator(
            '',
            ('subdir/',),
            'subdir',
            ('+ ***', '- *')
        )

    def test_star(self):
        """
        Wildcard in pathspec without glob magic
        """
        self._testTranslator(
            '',
            ('*.py',),
            '',
            ('+ **.py/***', '+ **.py', '- *')
        )

    def test_prefix(self):
        """
        Pathspec with common prefix
        """
        self._testTranslator(
            '',
            ('dir/*.py', 'dir/x.py'),
            'dir',
            ('+ **.py/***', '+ **.py', '+ x.py/***', '+ x.py', '- *')
        )

    def test_subdir(self):
        """
        Invoke in subdirectory
        """
        self._testTranslator(
            'hello world',
            ('*.py', '../x'),
            '',
            ('+ hello world/', '+ hello world/**.py/***', '+ hello world/**.py', '+ x/***', '+ x', '- *')
        )

    def test_exclude(self):
        """
        Exclude a file
        """
        self._testTranslator(
            '',
            (':!README.md',),
            '',
            ('- README.md/***', '- README.md', '+ ***'),
        )

    def test_exclude2(self):
        """
        Exclude a file in subdir
        """
        self._testTranslator(
            '',
            (':!docs/README.md',),
            '',
            ('- docs/README.md/***', '- docs/README.md', '+ docs/', '+ ***'),
        )

    def test_exclude3(self):
        """
        Exclude a file in subdir and include some file
        """
        self._testTranslator(
            'subdir',
            ('subsubdir/', ':!README.md'),
            'subdir',
            ('- README.md/***', '- README.md', '+ subsubdir/***', '- *'),
        )

    def _testTranslator(self, prefix, pathspec, common_prefix, filters):
        ps = PathSpec.parse(pathspec)
        translator = Translator(prefix, ps)
        translator.translate()

        self.assertEqual(translator.common_prefix, common_prefix)
        self.assertSequenceEqual(translator.filters, filters)
