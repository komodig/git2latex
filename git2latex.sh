#!/bin/bash

rm *.out.*
rm *.json

set -e

echo "activating venv..."
source venv/bin/activate

python githours.py -p 1
gvim --nofork workdays.json
gvim --nofork workdays.text.json
python githours.py -p 2

pdflatex bill-example.out.tex && evince bill-example.out.pdf &
