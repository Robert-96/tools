#!/bin/bash

# to-utf8.sh - A script to convert files to UTF-8 encoding and remove BOM
# Usage: ./to-utf8.sh <file1> <file2> ...
# This script will process each file passed as an argument, removing BOM if present and converting to UTF-8 encoding.

remove_bom() {
    # Function to remove BOM (Byte Order Mark) from a file
    # Usage: remove_bom <file>
    local file="$1"

    if [[ -f "$file" ]]; then
        # Check if the file starts with a BOM (Byte Order Mark)
        if head -c 3 "$file" | grep -q $'\xEF\xBB\xBF'; then
            # Remove the BOM by using sed to delete the first three bytes
            sed -i '1s/^\xEF\xBB\xBF//' "$file"
            echo "BOM removed from $file"
        else
            echo "No BOM found in $file"
        fi
    else
        echo "File $file does not exist."
    fi
}

convert_to_utf8() {
    # Function to convert a file to UTF-8 encoding
    # Usage: convert_to_utf8 <file>
    local file="$1"

    if [[ -f "$file" ]]; then
        # Convert the file to UTF-8 encoding using iconv
        iconv -f UTF-8 -t UTF-8 "$file" -o "$file"
        echo "Converted $file to UTF-8 encoding"
    else
        echo "File $file does not exist."
    fi
}


main() {
    # Main function to process each file passed as an argument
    if [[ $# -eq 0 ]]; then
        echo "Usage: $0 <file1> <file2> ..."
        exit 1
    fi

    for file in "$@"; do
        remove_bom "$file"
        convert_to_utf8 "$file"
    done
}

main "$@"
