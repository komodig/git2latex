#!/bin/bash

rm *.out.*
rm *.json

echo "activating venv..."
source venv/bin/activate

workdays="workdays.json"
template="bill-example.tex"
editor=gvim
viewer=evince

echo "*** 1st run to extract dates and messages from repositiries..."
python githours.py -w $workdays -t $template -p 1
echo "opening json results with '$editor'...to edit manually!"
for json in $workdays; do
  [ $editor == "gvim" ] && $editor --nofork $json || $editor $json;
done

echo "*** 2nd run to render template from json data..."
# redirect stderr to stdout and ignore the output in the original stdout
# so the output will only be the content in stderr
res_tex=`python githours.py -w $workdays -t $template -p 2 2>&1 > /dev/null`
echo "result: $res_tex"
res_pdf=`echo $res_tex | sed -e 's/\.tex/.pdf/'`
echo "pdf target: $res_pdf"
pdflatex -halt-on-error $res_tex && $viewer $res_pdf &
