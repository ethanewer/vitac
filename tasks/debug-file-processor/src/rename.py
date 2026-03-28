#!/usr/bin/env python3
"""Batch rename files with date prefix."""
import os
import re

def rename_files(directory):
    renamed = []
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            continue

        # Extract date from filename - BUG 2: too greedy, matches any digits
        match = re.search(r'(\d+)', filename)
        if match and len(match.group(1)) == 8:
            date_str = match.group(1)
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # Remove date from original name
            base, ext = os.path.splitext(filename)
            name_without_date = re.sub(r'_?\d{8}_?', '_', base).strip('_')
            new_name = f"{formatted_date}_{name_without_date}{ext}"

            # BUG 1: doesn't include directory in destination path
            os.rename(filepath, new_name)
            renamed.append((filename, new_name))
            print(f"Renamed: {filename} -> {new_name}")

    return renamed

if __name__ == "__main__":
    result = rename_files("/app/data/files/")
    print(f"\nRenamed {len(result)} files")

    # List directory after rename
    print("\nFiles in /app/data/files/:")
    for f in sorted(os.listdir("/app/data/files/")):
        print(f"  {f}")
