import sys
from argparse import ArgumentParser, SUPPRESS
from typing import Iterable, List

from typing.io import IO


def parse_arguments(args: List[str]) -> dict:
    parser = ArgumentParser(prog='seb-grep', description="grep implemented with python by seb", add_help=False)

    parser.add_argument(
        '-v',
        '--invert-match',
        help="Retrieve lines not matching the expr",
        default=False,
        action='store_true'
    )
    parser.add_argument(
        '-i',
        '--ignore-case',
        help="Ignore case when comparing file content with expr",
        default=False,
        action='store_true'
    )
    parser.add_argument(
        '-n',
        '--line-number',
        help="display line number as prefix",
        default=False,
        dest='number_prefix',
        action='store_true'
    )
    file_name_group = parser.add_mutually_exclusive_group()
    file_name_group.add_argument(
        '-H',
        '--with-filename',
        help="Print the filename for each match",
        default=None,
        dest="with_filename",
        action='store_true'
    )
    file_name_group.add_argument(
        '-h',
        '--no-filename',
        help="Do not print the filename for each match",
        default=None,
        dest="with_filename",
        action='store_false'
    )
    file_match_group = parser.add_mutually_exclusive_group()
    file_match_group.add_argument(
        '-l',
        '--files-with-matches',
        help="Suppress normal output; instead print the name of each input file from which output would normally have "
             "been printed.  The scanning will stop on the first match.",
        default=False,
        dest="only_files_with_matches",
        action='store_true'
    )
    file_match_group.add_argument(
        '-L',
        '--files-without-match',
        help="Suppress normal output; instead print the name of each input file from which output would normally have "
             "been printed.  The scanning will stop on the first match.",
        default=False,
        dest="only_files_without_match",
        action='store_true'
    )
    parser.add_argument('--help', dest='help', action='help', default=SUPPRESS, help='show this help message and exit')
    parser.add_argument('expr', help='Expression that file lines must match')
    parser.add_argument('file_paths', nargs='*', help="Files in which matches are searched")

    return vars(parser.parse_args(args))


class GrepConfig:

    def __init__(self, args: List[str]):

        params = parse_arguments(args)

        self.stdin: bool = False
        self.file_paths: List[str] = params['file_paths']
        if not self.file_paths:
            self.stdin = True
        self.expr: str = params['expr']
        self.ignore_case: bool = params['ignore_case']
        self.invert_match: bool = params['invert_match']
        self.number_prefix: bool = params['number_prefix']
        self.only_files_with_matches: bool = params['only_files_with_matches']
        self.only_files_without_match: bool = params['only_files_without_match']

        if params['with_filename'] is None:
            self.with_filename: bool = len(self.file_paths) > 1
        else:
            self.with_filename: bool = params['with_filename']

        base_expr: str = self.expr.lower() if self.ignore_case else self.expr
        self.comparable_expr: str= base_expr
        self.comparable_exprs: List[str] = base_expr.split('\n')


class GrepLine:
    """
    A line in a file
    """

    def __init__(self, file_name: str, n: int, line: str, grep_config: GrepConfig):
        self.file_name = file_name
        self.n = n
        self.line = line
        self.comparable_line = line.lower() if grep_config.ignore_case else line
        self.grep_config = grep_config

    def __str__(self) -> str:
        """
        format the GrepLine as string, according to formatting options
        """
        if self.grep_config.only_files_with_matches or self.grep_config.only_files_without_match:
            return f'{self.file_name}\n'

        content = []
        if self.grep_config.with_filename:
            content.append(self.file_name)
        if self.grep_config.number_prefix:
            content.append(str(self.n))
        content.append(self.line)
        return ':'.join(content)

    def __eq__(self, other):
        if not issubclass(type(other), GrepLine):
            return False
        if self.n != other.n:
            return False
        if self.line != other.line:
            return False
        if self.file_name != other.file_name:
            return False
        return True

    def match(self) -> bool:
        """
        Check if the line matches the expr, according to matching options passed to the command
        """
        match: bool
        for expr in self.grep_config.comparable_exprs:
            match = self.comparable_line.find(expr) != -1
            if match:
                return False if self.grep_config.invert_match else True

        return True if self.grep_config.invert_match else False


class GrepInput:

    def __init__(self, input_name: str, input_io: IO):
        self.input_name = input_name
        self.input_io = input_io


class SebGrep:

    def __init__(self, grep_config: GrepConfig):
        self.grep_config = grep_config

    def compute_inputs(self) -> List[GrepInput]:
        inputs: List[GrepInput]
        if self.grep_config.stdin:
            inputs = [GrepInput('stdin', sys.stdin)]
        else:
            inputs = list(map(lambda path: GrepInput(path, open(path, 'rt')), self.grep_config.file_paths))

        return inputs

    def grep(self):
        inputs: List[GrepInput] = self.compute_inputs()
        for grep_input in inputs:
            file_path = grep_input.input_name
            input_iterable = grep_input.input_io
            match_counter = 0
            try:
                for idx, line in enumerate(input_iterable):
                    grep_line = GrepLine(file_path, idx + 1, line, self.grep_config)
                    if grep_line.match():
                        match_counter += 1
                        if not self.grep_config.only_files_without_match:
                            yield grep_line
                        else:
                            break
                        if self.grep_config.only_files_with_matches:
                            break
            finally:
                if self.grep_config.only_files_without_match and match_counter == 0:
                    yield GrepLine(file_path, -1, '', self.grep_config)
                input_iterable.close()


def main(args: List[str]) -> None:

    grep_config = GrepConfig(args)
    seb_grep = SebGrep(grep_config)

    for result in seb_grep.grep():
        print(result, end='', file=sys.stdout)


if __name__ == '__main__':
    main(sys.argv[1:])
