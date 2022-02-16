# -*- coding: UTF-8 -*-

import os
import subprocess
import json
from datetime import datetime, timedelta
import sys
import locale
from argparse import ArgumentParser
from jinja2 import Environment, FileSystemLoader
from functools import reduce
from decimal import Decimal, ROUND_HALF_DOWN
from settings import *


commit_parse_format = '%a %b %d %H:%M:%S %Y %z'
commit_print_format = '%Y-%m-%d'


def daystr(date: datetime):
    return date.strftime(commit_print_format)


def _break_into_lines(line: str, max_length: int):
    """
    Recursively break long lines into a list of partial lines.
    (always keep some extra blank chars (e.g. -5) for new-line-chars)

    @param line: line which may exceed max length
    @return: list of lines
    """
    if len(line) >= max_length:
        try:
            x = line[:max_length].rindex(' ')      # align to whitespace to avoid words fragmentation
        except ValueError:
            x = max_length

        return [line[:x]] + _break_into_lines(line[x + 1:], max_length)
    else:
        return [line]

def worklogs_from_commits(commits):
    days = [(co.date, co.hours) for co in commits]
    return {day: hours for (day, hours) in sorted(list(set(days)))}

def load_worklogs_json(worklog_file):
    """
    @param worklog_file: json file with commit messages
    @return:
    """
    print('reading: ' + worklog_file)
    commits = []
    with open(worklog_file, 'r') as wlog:
        for line in [line.rstrip('\n') for line in wlog]:
            cjson = (json.loads(line))
            commits.append(Commit(**cjson))

    return commits

class Commit:
    def __init__(self, date: str, proj_name: str, hours=DAILY_HOURS, text=None):
        self.date = date
        self.hours = float(hours)
        self.text = '' if text is None else text
        self.proj_name = proj_name

    def __repr__(self):
        return '{} {} ({})'.format(self.date, self.text, self.proj_name)

    def serialize(self):
        return {'date': self.date, 'hours': str(self.hours), 'text': self.text, 'proj_name': self.proj_name}


class ProjectDays:
    def __init__(self, start_date: datetime, end_date: datetime, workspace: str=None, author: str=None, name: str=None, commits: list=None, parse=False):
        self.workspace = workspace
        self.start_date = start_date
        self.end_date = end_date
        self.author = author
        self.name = name
        self.commits = commits if commits is not None else list()
        self.__it = 0
        self.line_count = 1

        if parse:
            self.parse_commits()

    def parse_commits(self):
        os.chdir(self.workspace)
        print('entering workspace: {}'.format(os.getcwd()))
        if not os.path.exists(os.path.join(os.getcwd(), '.git')):
            print('error: not a git workspace!')
            exit(1)

        s = subprocess.check_output('git log --author="{}"'.format(self.author), shell=True)
        s = s.decode('utf-8')

        valid_date = False
        for line in s.split('\n'):
            if line.startswith('commit') or line.startswith('Author') or line.strip() == '':
                continue
            else:
                if line.startswith('Date'):
                    commit_date = datetime.strptime(line.replace('Date:', '').strip(), commit_parse_format)
                    if commit_date < self.start_date or (self.end_date + timedelta(days=1)) <= commit_date:
                        valid_date = False
                        continue
                    else:
                        self.commits.append(Commit(daystr(commit_date), self.name))
                        valid_date = True
                else:
                    # handle the actual commit message
                    if valid_date:
                        self.commits[-1].text += ' ' + line.strip().replace('\n', ' ')

    def write_worklogs_json(self, worklog_file):
        print('writing: ' + worklog_file)
        with open(worklog_file, 'w') as wlog:
            for commit in self.commits:
                wlog.write(json.dumps(commit.serialize()) + '\n')

    def _worklogs_context(self, line_length):
        text_lines = []
        for day in self.worklogs.keys():
            lines = self._logs_for_day(day, line_length)
            # first line per day with date and hours
            hours = str(self.worklogs[day])
            if hours.endswith(".0"):
                hours = hours[:-2]
            text_lines.append({'date': day, 'hours': hours, 'text': lines.pop(0), 'count': self.line_count % PAGE_LINES})
            self.line_count += 1
            for lin in lines:
                text_lines.append({'date': '', 'hours': '','text': lin, 'count': self.line_count % PAGE_LINES})
                self.line_count += 1

        return text_lines

    def _template_context(self, hourly_rate, line_length):
        total_hours = reduce(lambda x,y: x + y, [ float(x) for x in self.worklogs.values() ])
        fee = Decimal(total_hours * hourly_rate)
        fee = fee.quantize(Decimal('.01'), rounding=ROUND_HALF_DOWN)
        tax = Decimal(fee * Decimal(VAT_PERCENT/100))
        tax = tax.quantize(Decimal('.01'), rounding=ROUND_HALF_DOWN)

        locale.setlocale(locale.LC_NUMERIC, '')

        context = {
                'date': daystr(self.end_date),
                'hours': total_hours,
                'rate': hourly_rate,
                'tax_rate': VAT_PERCENT,
                'fee': locale.format('%.2f', fee, grouping=True),
                'tax': locale.format('%.2f', tax, grouping=True),
                'total': locale.format('%.2f', fee + tax, grouping=True),
                'worklogs': self._worklogs_context(line_length)
        }
        return context

    def render_template(self, template_dir, template_file, hourly_rate, line_length):
        context = self._template_context(hourly_rate, line_length)
        template_loader = FileSystemLoader(template_dir)
        j2env = Environment(
            block_start_string = '\BLOCK{',
            block_end_string = '}',
            variable_start_string = '\VAR{',
            variable_end_string = '}',
            comment_start_string = '\#{',
            comment_end_string = '}',
            line_statement_prefix = '\RUN',
            line_comment_prefix = '%#',
            autoescape = False,
            loader = template_loader,
            trim_blocks = True
        )
        print('render template: ' + template_file)
        template = j2env.get_template(template_file)
        latex = template.render(context)
        latex_file = os.path.join(template_dir, template_file.replace('.tex', '.out.tex'))
        print('writing output file: ' + latex_file)
        with open(latex_file, 'w') as tf:
            tf.write(latex)

        return latex_file

    def _logs_for_day(self, day, line_length):
        lines_orig = [ {'text':c.text, 'name':c.proj_name } for c in list(filter(lambda x: x.date == day, self.commits)) ]
        lines_mod = []
        for line in lines_orig:
            line_text = line['text'].replace('_', '-')    # no underscores when using pdflatex
            line_text = line_text.replace('%', '')    # no % when using pdflatex
            #print(line_text)
            new_lines = _break_into_lines(line_text, line_length)
            # append proj-name if there are multiple projects
            if len(PROJECTS) > 1:
                new_lines[-1] = '{} ({})'.format(new_lines[-1], line['name'])
            #print(new_lines)
            #print('------------------')

            lines_mod += new_lines

        return lines_mod

    def __repr__(self):
        return '{} {} {} {}'.format(self.name, daystr(self.start_date), daystr(self.end_date), len(self))

    def __iter__(self):
        self.__it = 0
        return self

    def __next__(self):
        try:
            item = self.commits[self.__it]
        except IndexError:
            raise StopIteration

        self.__it += 1
        return item

    def __add__(self, other):
        sdate = self.start_date if self.start_date < other.start_date else other.start_date
        edate = self.end_date if self.end_date > other.end_date else other.end_date

        return ProjectDays(sdate, edate, name=self.name, commits=self.commits + other.commits)

    def __len__(self):
        return len(self.commits)

if __name__ == '__main__':
    if not sys.version.startswith('3'):
        print('please use python3!')
        exit(1)

    parser = ArgumentParser()
    parser.add_argument('-p', '--phase', default='1', choices=['1', '2'])
    parser.add_argument('-w', '--workdays', default='workdays.json')
    parser.add_argument('-t', '--template', default='bill-example.tex')

    args = parser.parse_args()

    template = os.path.basename(args.template)
    template_dir = os.path.dirname(args.template)
    if template_dir == '':
        template_dir = os.getcwd()

    if os.path.dirname(args.workdays) == '':
        args.workdays = os.path.join(os.getcwd(), args.workdays)

    sdate = datetime.strptime(START_DATE + ' +0100', '%Y-%m-%d %z')
    edate = datetime.strptime(END_DATE + ' +0100', '%Y-%m-%d %z')

    project_list = []
    for proj in PROJECTS:
        project_list.append(ProjectDays(sdate, edate, **proj, parse=True))

    all_commits = ProjectDays(sdate, edate, name='all')
    for proj in project_list:
        all_commits += proj

    if args.phase == '1':
        print('assuming {} hours per day'.format(DAILY_HOURS))
        all_commits.write_worklogs_json(args.workdays)

    if args.phase == '2':
        commits = load_worklogs_json(args.workdays)
        all_commits = ProjectDays(sdate, edate, name='all', commits=commits)
        all_commits.worklogs = worklogs_from_commits(commits)
        of = all_commits.render_template(template_dir, args.template, HOURLY_RATE, LINE_LENGTH)
        exit(of)

