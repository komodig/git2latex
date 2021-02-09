# -*- coding: UTF-8 -*-

import os

BASE_DIR = os.path.join('/', 'home', 'karl', 'workspace')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'git2latex', 'bill-example.tex')
PROJECTS = [
    {
        'workspace': 'reeknersprook',
        'name': 'rs'
    },
    {
        'workspace': 'avr-uno',
        'name': 'avr'
    }
]
WORK_RECORDS = os.path.join(BASE_DIR, 'git2latex', 'workdays.json')
START_DATE = '2018-01-01'
END_DATE = '2018-12-31'
DAILY_HOURS = 8
VAT_PERCENT = 16
PAGE_LINES = 44

