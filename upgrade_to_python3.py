#!/usr/bin/env python3

import json
import os
import sys
from subprocess import CalledProcessError, run
from typing import Iterable, Tuple, Union

from generate_commit_msg import generate_commit_msg

print('=' * 83)  #  Mark the start of Python execution in the Action logfile

NEW_BRANCH_NAME = 'modernize-Python-2-codes'

# https://github.com/PythonCharmers/python-future/blob/master/src/libfuturize/fixes/__init__.py
# An even safer subset of fixes than `futurize --stage1`
SAFE_FIXES = set('lib2to3.fixes.fix_' + fix for fix
                 in """apply except exec exitfunc funcattrs has_key idioms intern isinstance
                       methodattrs ne numliterals paren reduce renames repr standarderror
                       sys_exc throw tuple_params types xreadlines""".split())


# run command and return its output
def cmd(in_cmd: Union[str, Iterable[str]], check: bool = True, err_text: bool = False) -> str:
    """Run a command and return its output or raise CalledProcessError"""
    print('$', in_cmd)
    if isinstance(in_cmd, str):
        in_cmd = in_cmd.split()
    result = run(in_cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    if check:
        result.check_returncode()  # will raise subprocess.CalledProcessError()
    # return '\n'.join(result.stdout.splitlines())
    return result.stdout + (result.stderr if err_text else '')


def flake8_tests() -> str:
    return cmd('flake8 . --show-source --statistics --select=E999', check=False)


def files_with_print_issues(flake8_results: str) -> Tuple[str]:
    """Walk backwards through flake8 output to find those files that have old style print statements."""
    file_paths = set()
    next_line_contains_file = False
    # reverse the lines so we can move from last to first
    for line in reversed(flake8_results.splitlines()):
        if next_line_contains_file:
            file_paths.add(line.split(':')[0])
        next_line_contains_file = 'print ' in line
    return tuple(sorted(file_paths))


def fix_print(file_paths: Iterable[str]) -> str:
    if not file_paths:
        return ''
    return cmd('futurize -f libfuturize.fixes.fix_print_with_import -w ' +
               ' '.join(file_paths))


def fix_safe_fixes() -> str:
    """This is an even safer subset of futurize --stage1 -w ."""
    return cmd(f"futurize -f {' -f '.join(SAFE_FIXES)} "
               "-f libfuturize.fixes.fix_next_call -w .")


# def checkout_new_branch(branch_name: str = '') -> str:
#     branch_name = branch_name or NEW_BRANCH_NAME
#     return cmd(f'git checkout -b {branch_name}')


# def git_remote_add_upstream(upstream_url: str) -> str:
#     return cmd(f'git remote add upstream {upstream_url}')


# print('os.environ: ' + '\n            '.join(f'{key}: {os.getenv(key)}'
#                                              for key in sorted(os.environ)))

with open(os.getenv('GITHUB_EVENT_PATH')) as in_file:
    github_event = json.load(in_file)
# print(json.dumps(github_event, sort_keys=True, indent=2))

flake8_results = flake8_tests()
assert flake8_results, """No Python 3 syntax errors or undefined names were found.
    This Action can not propose any further changes."""
file_paths = files_with_print_issues(flake8_results)
diff = fix_print(file_paths) if file_paths else fix_safe_fixes()
push_result = ''
if '+' not in diff:
    print('diff is empty!')
print('Success!')
print('\n'.join(line.replace('remote:', '')
      for line in push_result.splitlines()[1:4]))
