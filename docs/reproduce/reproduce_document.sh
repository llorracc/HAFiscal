#!/bin/bash
source ./reproduce/reproduce_environment_texlive.sh

pdflatex HAFiscal
bibtex   HAFiscal
pdflatex HAFiscal
pdflatex HAFiscal

