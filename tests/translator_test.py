import logging
import unittest


class TranslatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.basicConfig(level=logging.DEBUG)

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

    @unittest.skip("not implemented")
    def test_glob(self):
        self._testTranslator(
            '',
            (':(glob)*.py',),
            '',
            ('+ /*.py', '- *'),
        )

    @unittest.skip("not implemented")
    def test_glob2(self):
        self._testTranslator(
            '',
            (':(glob)subdir',),
            'subdir',
            ('+ ***', '- *'),
        )

    @unittest.skip("not implemented")
    def test_glob3(self):
        self._testTranslator(
            '',
            (':(glob)subdir*',),
            '',
            ('+ subdir*', '- *',)
        )

    @unittest.skip("not implemented")
    def test_glob3v2(self):
        self._testTranslator(
            '',
            (':(glob)subdir*/',),
            '',
            ('+ subdir*/', '- *'),
        )

    @unittest.skip("not implemented")
    def test_glob4(self):
        self._testTranslator(
            '',
            (':(glob)subdir*/*',),
            '',
            ('+ subdir*/*', '- *'),
        )

    def test_top_file(self):
        """
        Select a file from the repo root
        """
        self._testTranslator(
            'subdir',
            (':/subdir2/file',),
            'subdir2',
            ('+ file/***', '+ file', '- *'),
        )

    def test_top_dir(self):
        """
        Select sibling directory of the current directory
        """
        self._testTranslator(
            'subdir',
            (':/subdir2/',),
            'subdir2',
            ('+ ***', '- *'),
        )

    def test_top2(self):
        """
        Exclude a sibling directory of the current directory
        """
        self._testTranslator(
            'subdir',
            (':!/subdir',),
            '',
            ('- subdir/***', '- subdir', '+ ***'),
        )

    def test_top3(self):
        """
        Mixing including and excluding
        """
        self._testTranslator(
            'subdir',
            (':!/subdir', 'subsubdir'),
            '',
            ('- subdir/***', '- subdir', '+ subdir/', '+ subdir/subsubdir/***', '+ subdir/subsubdir', '- *'),
        )

    def test_top3v2(self):
        """
        Mixing including and excluding with tailing slash
        """
        self._testTranslator(
            'subdir',
            (':!/subdir/', 'subsubdir'),
            'subdir',
            ('- ***', '+ subsubdir/***', '+ subsubdir', '- *'),
        )

    def _testTranslator(self, prefix, pathspec, common_prefix, filters):
        from gitrsync.pathspec import PathSpec
        from gitrsync.translator import Translator

        ps = PathSpec.parse(pathspec)
        translator = Translator(prefix, ps)
        translator.translate()

        self.assertEqual(translator.common_prefix, common_prefix)
        self.assertSequenceEqual(translator.filters, filters)
