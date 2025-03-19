#!/bin/bash

[[ -e HAFiscal-body.tex ]] && rm HAFiscal-body.tex

cd /Volumes/Data/Papers/HAFiscal/HAFiscal-Latest/Subfiles/

touch HAFiscal-body.tex

for f in Intro literature Model Parameterization HANK Comparing-policies Conclusion; do
    cat $f.tex >> HAFiscal-body.tex
done

	 
