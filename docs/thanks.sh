#!/usr/bin/env bash

# 1) Start a fresh acknowledgments file
[[ -e acknowledgments-snippets.tex ]] && rm acknowledgments-snippets.tex
touch acknowledgments-snippets.tex
echo "The authors would like to thank workshop audiences at %" >> acknowledgments-snippets.tex

# 2) List your snippet basenames
for snippet in thanks-talks_CDC thanks-talks_DuW thanks-talks_EC thanks-talks_HT
do
  # Check if the snippet file exists and is nonempty
  if [ -s "Subfiles/$snippet.tex" ]; then
    # It's nonempty! So append an input reference:
    echo "\\input{Subfiles/$snippet.tex}%" >> acknowledgments-snippets.tex
    # Optionally also add commas, 'and', etc.
  fi
done

echo "and \\input{Subfiles/thanks-talks_IF}" >> acknowledgments-snippets.tex
echo -n " for valuable feedback.  The authors would like to thank " >> acknowledgments-snippets.tex

for snippet in thanks-persons_CDC thanks-persons_DuW thanks-persons_EC thanks-persons_HT 
do
  # Check if the snippet file exists and is nonempty
  if [ -s "Subfiles/$snippet.tex" ]; then
    # It's nonempty! So append an input reference:
    echo "\\input{Subfiles/$snippet.tex}%" >> acknowledgments-snippets.tex
    # Optionally also add commas, 'and', etc.
  fi
done
echo -n ", and {\\input{Subfiles/thanks-persons_IF}} " >> acknowledgments-snippets.tex
echo " for insightful comments on draft versions of the paper." >> acknowledgments-snippets.tex

# You can similarly handle thanks-persons_... or anything else
