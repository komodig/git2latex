#!/bin/bash

rm *.out.*
rm *.json

set -e

echo "activating venv..."
source venv/bin/activate

workdays="workdays.json"
messages="messages.json"

python githours.py -w $workdays -m $messages -p 1
gvim --nofork $workdays
gvim --nofork $messages
python githours.py -w $workdays -m $messages -p 2

pdflatex bill-example.out.tex && evince bill-example.out.pdf &
