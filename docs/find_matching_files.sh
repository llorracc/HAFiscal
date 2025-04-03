#!/bin/bash

# Script to find all files matching patterns in .cursor-rules and display them in a tree structure
# Usage: ./find_matching_files.sh [root_directory]

set -e

ROOT_DIR="${1:-.}"
CURSOR_RULES=".cursor-rules"
OUTPUT_FILE="file_structure.txt"

echo "Scanning for files matching patterns in $CURSOR_RULES starting from $ROOT_DIR"
echo "Results will be saved to $OUTPUT_FILE"

# Check if .cursor-rules exists
if [ ! -f "$CURSOR_RULES" ]; then
    echo "Error: $CURSOR_RULES file not found!"
    exit 1
fi

# Extract patterns from .cursor-rules, filtering out comments and empty lines
include_patterns=()
exclude_patterns=()

while IFS= read -r line; do
    # Skip comments and empty lines
    if [[ "$line" =~ ^[[:space:]]*# || -z "${line// }" ]]; then
        continue
    fi
    
    # Handle exclusion patterns (lines starting with !)
    if [[ "$line" == !* ]]; then
        exclude_patterns+=("${line#!}")
    else
        # Add inclusion pattern to array
        include_patterns+=("$line")
    fi
done < "$CURSOR_RULES"

# If no patterns were found
if [ ${#include_patterns[@]} -eq 0 ]; then
    echo "No valid inclusion patterns found in $CURSOR_RULES"
    exit 1
fi

echo "Found ${#include_patterns[@]} inclusion patterns and ${#exclude_patterns[@]} exclusion patterns in $CURSOR_RULES"

# Create a temporary directory for processing
temp_dir=$(mktemp -d)
trap 'rm -rf "$temp_dir"' EXIT

# Process include patterns
include_list="$temp_dir/include_list.txt"
touch "$include_list"

echo "Finding files matching inclusion patterns..."
for pattern in "${include_patterns[@]}"; do
    # Handle **/*.ext pattern
    if [[ "$pattern" == "**/"* ]]; then
        ext="${pattern#**/}"
        find "$ROOT_DIR" -type f -name "$ext" >> "$include_list"
    else
        # Handle other glob patterns (less common in cursor-rules)
        find "$ROOT_DIR" -type f -path "$pattern" >> "$include_list"
    fi
done

# Sort and remove duplicates
sort -u "$include_list" -o "$include_list"
included_count=$(wc -l < "$include_list")
echo "Found $included_count files matching inclusion patterns"

# Process exclude patterns
if [ ${#exclude_patterns[@]} -gt 0 ]; then
    echo "Applying exclusion patterns..."
    exclude_list="$temp_dir/exclude_list.txt"
    touch "$exclude_list"
    
    for pattern in "${exclude_patterns[@]}"; do
        # Handle wildcard directory exclusions (like *resources/**)
        if [[ "$pattern" == *\**/** ]]; then
            # Extract the directory pattern before /**
            dir_pattern="${pattern%/**}"
            # Remove the * at the beginning if present
            search_pattern="${dir_pattern#\*}"
            
            # Find all directories that end with the pattern
            while IFS= read -r dir; do
                if [[ "$dir" == *"$search_pattern" ]]; then
                    # Find all files under these directories
                    find "$dir" -type f >> "$exclude_list" 2>/dev/null || true
                fi
            done < <(find "$ROOT_DIR" -type d)
            
        # Handle regular directory exclusions (like .specstory/** or Code/**)
        elif [[ "$pattern" == */** ]]; then
            # Extract the directory name before /**
            dir_name="${pattern%/**}"
            # Find all files under this directory
            find "$ROOT_DIR/$dir_name" -type f 2>/dev/null >> "$exclude_list" || true
        else
            # Handle other exclusion patterns
            find "$ROOT_DIR" -path "$ROOT_DIR/$pattern" >> "$exclude_list" || true
        fi
    done
    
    # Sort and remove duplicates
    if [ -s "$exclude_list" ]; then
        sort -u "$exclude_list" -o "$exclude_list"
        excluded_count=$(wc -l < "$exclude_list")
        echo "Found $excluded_count files matching exclusion patterns"
        
        # Remove excluded files from the inclusion list
        final_list="$temp_dir/final_list.txt"
        comm -23 "$include_list" "$exclude_list" > "$final_list"
        final_count=$(wc -l < "$final_list")
        echo "Final file count after applying exclusions: $final_count"
    else
        final_list="$include_list"
        final_count=$included_count
        echo "No files matched exclusion patterns"
    fi
else
    final_list="$include_list"
    final_count=$included_count
    echo "No exclusion patterns specified"
fi

echo "Generating directory tree structure..."

# Create the directory tree structure
{
    echo "Directory structure containing files matching patterns in $CURSOR_RULES:"
    echo "--------------------------------------------------------------------------------"
    echo "Root: $ROOT_DIR"
    echo "--------------------------------------------------------------------------------"
    
    # Process the file list to create a tree structure
    prev_dirs=()
    while IFS= read -r file; do
        # Get relative path
        rel_path="${file#$ROOT_DIR/}"
        
        # Split path into directories
        IFS='/' read -ra dirs <<< "$(dirname "$rel_path")"
        
        # Determine common prefix length with previous path
        common_len=0
        for ((i=0; i<${#dirs[@]} && i<${#prev_dirs[@]}; i++)); do
            if [[ "${dirs[i]}" == "${prev_dirs[i]}" ]]; then
                ((common_len++))
            else
                break
            fi
        done
        
        # Print directories that are different from previous path
        for ((i=common_len; i<${#dirs[@]}; i++)); do
            indent=$(printf "%$((i*2))s" "")
            echo "${indent}└── ${dirs[i]}/"
        done
        
        # Print the file
        file_name=$(basename "$file")
        indent=$(printf "%$((${#dirs[@]}*2))s" "")
        echo "${indent}    └── $file_name"
        
        # Save current dirs for next iteration
        prev_dirs=("${dirs[@]}")
    done < "$final_list"
    
    echo "--------------------------------------------------------------------------------"
    echo "Total: $final_count files"
    echo "Inclusion patterns: ${include_patterns[*]}"
    echo "Exclusion patterns: ${exclude_patterns[*]}"
} > "$OUTPUT_FILE"

echo "Tree structure has been saved to $OUTPUT_FILE"
echo "You can now share this file with an AI to provide context about your project structure."

echo "Done!" 