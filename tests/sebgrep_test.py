import os
import sys
import unittest
from unittest import TestCase
from typing import List
from tempfile import mkstemp

import sebgrep


class MyOut:
    """
    Fake stdout
    """

    _lines: List[str] = []

    def write(self, text: str):
        # FIXME find why empty texts are written
        if text:
            self._lines.append(text)

    def get_lines(self):
        return self._lines

    def getvalue(self):
        return '\n'.join(self._lines)

    def flush(self):
        pass


class SebGrepTest(TestCase):

    small_file_path: str = ''
    large_file_path: str = ''
    my_stdout: MyOut = MyOut()
    old_stdout = None

    @classmethod
    def setUpClass(cls) -> None:
        (fd, path) = mkstemp(text=True)
        cls.small_file_path = path

        with os.fdopen(fd, 'w') as f:
            f.write("Je teste les fichiers temporaires\n")
            f.write("Seb danse le mia\n")
            f.write("seb aime Yanis\n")
            f.write("Yanis aime son Papa seb\n")
            f.write("Seb sébien\n")
            f.write("Matis et Yanis sont des fadas")

        (fd, path) = mkstemp(text=True)
        cls.large_file_path = path
        with os.fdopen(fd, 'w') as f:
            for x in range(10_000):
                f.write("Je teste les fichiers temporaires\n")
                f.write("Seb danse le mia\n")
                f.write("seb aime Yanis\n")
                f.write("Yanis aime son Papa seb\n")
                f.write("Seb sébien\n")
                f.write("Matis et Yanis sont des fadas")

    def tearDown(self) -> None:
        self.my_stdout.get_lines().clear()
        sys.stdout = self.old_stdout

    def setUp(self) -> None:
        self.old_stdout = sys.stdout
        sys.stdout = self.my_stdout

    @classmethod
    def tearDownClass(cls) -> None:
        os.remove(cls.small_file_path)
        os.remove(cls.large_file_path)

    def test_nominal(self) -> None:
        test_args = ["Seb", self.small_file_path]
        sebgrep.main(test_args)
        self.assertIn("Seb danse le mia\n", self.my_stdout.get_lines())
        self.assertNotIn("seb aime Yanis\n", self.my_stdout.get_lines())

    def test_nominal_large_file(self):
        test_args = ["Seb", self.large_file_path]
        sebgrep.main(test_args)
        self.assertIn("Seb danse le mia\n", self.my_stdout.get_lines())
        self.assertNotIn("seb aime Yanis\n", self.my_stdout.get_lines())

    def test_ignore_case(self):
        test_args = ["-i", "Seb", self.small_file_path]
        sebgrep.main(test_args)
        self.assertIn("Seb danse le mia\n", self.my_stdout.get_lines())
        self.assertIn("seb aime Yanis\n", self.my_stdout.get_lines())
        self.assertIn("Yanis aime son Papa seb\n", self.my_stdout.get_lines())
        self.assertNotIn("Je teste les fichiers temporaires\n", self.my_stdout.get_lines())
        self.assertEqual(4, len(self.my_stdout.get_lines()))

    def test_grep_config_ignore_case_only(self):
        grep_config = sebgrep.GrepConfig(["-i", "Seb", self.small_file_path])
        self.assertTrue(grep_config.ignore_case)
        self.assertFalse(grep_config.invert_match)
        self.assertFalse(grep_config.with_filename)

    def test_grep_config_invert_match_only(self):
        grep_config = sebgrep.GrepConfig(["-v", "Seb", self.small_file_path])
        self.assertTrue(grep_config.invert_match)
        self.assertFalse(grep_config.ignore_case)
        self.assertFalse(grep_config.with_filename)

    def test_grep_config_auto_with_filename(self):
        """
        When multiple file paths are given as arguments, results will be automatically prefixed with filenames
        """
        grep_config = sebgrep.GrepConfig(["Seb", "/to/path1", "/to/path2"])
        self.assertEqual("Seb", grep_config.expr)
        self.assertTrue(len(grep_config.file_paths) > 1)
        self.assertTrue(grep_config.with_filename)
        self.assertFalse(grep_config.invert_match)
        self.assertFalse(grep_config.ignore_case)

    def test_grep_config_only_files_with_matches(self):
        grep_config = sebgrep.GrepConfig(["-l", "Seb", "/to/path1"])
        self.assertTrue(grep_config.only_files_with_matches)
        self.assertFalse(grep_config.with_filename)
        self.assertFalse(grep_config.invert_match)
        self.assertFalse(grep_config.ignore_case)

    def test_grep_config_no_file(self):
        grep_config = sebgrep.GrepConfig(["def"])
        self.assertTrue(grep_config.stdin == True)

    def test_find_matching_content_only_files(self):
        grep_config = sebgrep.GrepConfig(["-l", "seb", self.small_file_path])
        seb_grep = sebgrep.SebGrep(grep_config)
        result = list(seb_grep.grep())
        self.assertEqual(1, len(result))
        self.assertEqual(f'{self.small_file_path}', result[0].file_name)

    def test_find_matching_content_not_matching_file_found(self):
        grep_config = sebgrep.GrepConfig(["-L", "macarena", self.small_file_path])
        seb_grep = sebgrep.SebGrep(grep_config)
        result = list(seb_grep.grep())
        self.assertEqual(1, len(result))
        self.assertEqual(self.small_file_path, result[0].file_name)
        self.assertEqual(f'{self.small_file_path}\n', str(result[0]))

    def test_find_matching_content_not_matching_file_not_found(self):
        grep_config = sebgrep.GrepConfig(["-L", "seb", self.small_file_path])
        seb_grep = sebgrep.SebGrep(grep_config)
        result = list(seb_grep.grep())
        self.assertEqual(0, len(result))
        # self.assertEqual(f'{self.small_file_path}', result[0].file_name)

    def test_find_matching_content_multiple_expr(self):
        grep_config = sebgrep.GrepConfig(["seb\nmia", self.small_file_path])
        seb_grep = sebgrep.SebGrep(grep_config)
        result = list(seb_grep.grep())
        self.assertEqual(3, len(result))
        str_lines = map(str, result)
        self.assertIn('Seb danse le mia\n', str_lines)
        self.assertIn('seb aime Yanis\n', str_lines)
        self.assertIn('Yanis aime son Papa seb\n', str_lines)

    def test_format_grep_line_include_file_name(self):
        grep_config = sebgrep.GrepConfig(["-H", "mia", self.small_file_path])
        seb_grep = sebgrep.SebGrep(grep_config)
        result = list(seb_grep.grep())
        self.assertEqual(1, len(result))
        self.assertEqual(f'{self.small_file_path}:Seb danse le mia\n', str(result[0]))

    def test_format_grep_line_include_line_number(self):
        grep_config = sebgrep.GrepConfig(["-n", "mia", self.small_file_path])
        seb_grep = sebgrep.SebGrep(grep_config)
        result = list(seb_grep.grep())
        self.assertEqual(1, len(result))
        expected_line = sebgrep.GrepLine(self.small_file_path, 2, 'Seb danse le mia\n', grep_config)
        self.assertEqual(expected_line, result[0])

    def test_format_grep_line_include_file_name_and_line_number(self):
        grep_config = sebgrep.GrepConfig(["-Hn", "mia", self.small_file_path])
        seb_grep = sebgrep.SebGrep(grep_config)
        result = list(seb_grep.grep())
        self.assertEqual(1, len(result))
        self.assertEqual(f'{self.small_file_path}:{str(2)}:Seb danse le mia\n', str(result[0]))

    def test_comparable_exprs_single_expr(self):
        grep_config = sebgrep.GrepConfig(["-Hn", "mia", self.small_file_path])
        self.assertEqual(1, len(grep_config.comparable_exprs))

    def test_comparable_exprs_2_exprs(self):
        grep_config = sebgrep.GrepConfig(["-Hn", "mia\ndef", self.small_file_path])
        self.assertEqual(2, len(grep_config.comparable_exprs))

    def test_comparable_exprs_3_exprs(self):
        grep_config = sebgrep.GrepConfig(["-Hn", "mia\ndef\nbisous", self.small_file_path])
        self.assertEqual(3, len(grep_config.comparable_exprs))

    def test_grep_line_equal_not_subclass(self):
        grep_config = sebgrep.GrepConfig(["expr", '/path/to/file'])
        grep_line = sebgrep.GrepLine('', 1, '', grep_config)
        self.assertNotEqual(grep_line, 'prout')

    def test_grep_line_equal_different_filename(self):
        grep_config = sebgrep.GrepConfig(["expr", '/path/to/file1', '/path/to/file2'])
        grep_line1 = sebgrep.GrepLine('/path/to/file1', 1, 'hello world', grep_config)
        grep_line2 = sebgrep.GrepLine('/path/to/file2', 1, 'hello world', grep_config)
        self.assertNotEqual(grep_line1, grep_line2)

    def test_grep_line_equal_different_line_number(self):
        grep_config = sebgrep.GrepConfig(["expr", '/path/to/file'])
        grep_line1 = sebgrep.GrepLine('/path/to/file', 1, 'hello world', grep_config)
        grep_line2 = sebgrep.GrepLine('/path/to/file', 2, 'hello world', grep_config)
        self.assertNotEqual(grep_line1, grep_line2)

    def test_grep_line_equal_different_line_content(self):
        grep_config = sebgrep.GrepConfig(["expr", '/path/to/file'])
        grep_line1 = sebgrep.GrepLine('/path/to/file', 1, 'hello world', grep_config)
        grep_line2 = sebgrep.GrepLine('/path/to/file', 1, 'hello worlde', grep_config)
        self.assertNotEqual(grep_line1, grep_line2)

    def test_seb_grep_compute_inputs_onefile(self):
        try:
            file_path = self.small_file_path
            grep_config = sebgrep.GrepConfig(["expr", file_path])
            seb_grep = sebgrep.SebGrep(grep_config)
            result = seb_grep.compute_inputs()
            self.assertEqual(1, len(result))
            self.assertEqual(result[0].input_name, file_path)
        finally:
            result[0].input_io.close()

    def test_seb_grep_compute_inputs_multiple_files(self):
        try:
            grep_config = sebgrep.GrepConfig(["expr", self.small_file_path, self.large_file_path])
            seb_grep = sebgrep.SebGrep(grep_config)
            result = seb_grep.compute_inputs()
            self.assertEqual(2, len(result))
        finally:
            result[0].input_io.close()
            result[1].input_io.close()

    def test_seb_grep_compute_inputs_no_file(self):
        grep_config = sebgrep.GrepConfig(["expr"])
        seb_grep = sebgrep.SebGrep(grep_config)
        result = seb_grep.compute_inputs()
        self.assertEqual(1, len(result))
        self.assertEqual(result[0].input_name, 'stdin')

if __name__ == '__main__':
    unittest.main('sebgrep_test')
