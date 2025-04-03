#!/bin/bash

# Script to generate a properly formatted .cursor/rules file based on file_structure.txt
# Usage: ./make_cursor-rules.sh [output_file]

set -e

FILE_STRUCTURE="file_structure.txt"
OUTPUT_DIR=".cursor/rules"
OUTPUT_FILE="${1:-$OUTPUT_DIR/project-files.md}"

echo "Creating Cursor rules file based on $FILE_STRUCTURE"

# Check if file_structure.txt exists
if [ ! -f "$FILE_STRUCTURE" ]; then
    echo "Error: $FILE_STRUCTURE not found!"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Extract inclusion patterns from file_structure.txt
INCLUSION_PATTERNS=$(grep "Inclusion patterns:" "$FILE_STRUCTURE" | sed 's/Inclusion patterns: //')

# Extract exclusion patterns from file_structure.txt
EXCLUSION_PATTERNS=$(grep "Exclusion patterns:" "$FILE_STRUCTURE" | sed 's/Exclusion patterns: //')

# Convert patterns into an array
IFS=' ' read -ra PATTERN_ARRAY <<< "$INCLUSION_PATTERNS"

# Create the rules file
{
    echo "# HAFiscal Project - AI Access Rules"
    echo ""
    echo "This file defines which files in the project should be accessible to the AI assistant."
    echo ""
    echo "## File Patterns"
    echo ""

    # Add each inclusion pattern with the "globs:" prefix
    for pattern in "${PATTERN_ARRAY[@]}"; do
        echo "globs: $pattern"
    done
    
    echo ""
    echo "## Excluded Patterns"
    echo ""
    
    # Convert exclusion patterns into an array
    IFS=' ' read -ra EXCLUSION_ARRAY <<< "$EXCLUSION_PATTERNS"
    
    # If we have exclusion patterns, add them with "ignore:" prefix
    if [ ${#EXCLUSION_ARRAY[@]} -gt 0 ]; then
        for pattern in "${EXCLUSION_ARRAY[@]}"; do
            echo "ignore: $pattern"
        done
    else
        echo "# No exclusion patterns defined"
    fi
    
    echo ""
    echo "## Project Structure"
    echo ""
    echo "This rules file is based on the project structure as of $(date)"
    echo ""
    echo "```"
    # Include a summary of the directory structure (first 20 lines)
    head -n 20 "$FILE_STRUCTURE" | tail -n +5
    echo "..."
    echo "```"
    
} > "$OUTPUT_FILE"

echo "Cursor rules file created at: $OUTPUT_FILE"
echo "Add this file to your project to give the AI assistant access to your files."
echo ""
echo "The file format follows Cursor's syntax with:"
echo "- globs: for inclusion patterns"
echo "- ignore: for exclusion patterns"
echo ""
echo "Done!" 