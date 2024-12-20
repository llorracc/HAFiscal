# -*- mode: sh; sh-shell: bash; -*-
# Google 'latexmk latexmkrc' for explanation of this config file
# or see https://mg.readthedocs.io/latexmk.html
# 
# latexmk at unix command line will compile the paper
$bibtex_silent_switch = '-terse';
$do_cd = 1;
$clean_ext = "bbl nav out snm tmp 4tc 4ct out log fls fdb_latexmk synctex.gz ps out.ps lg out";
$bibtex_use=2;
$pdf_mode = 1;
$rc_report = 1;
#@default_files = ('HAFiscal.tex');
$pdflatex="pdflatex -interaction=nonstopmode %O %S";
$aux_out_dir_report = 1;
$silent  = 0;
#warn "PATH = '$ENV{PATH}'\n";
