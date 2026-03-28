#!/bin/bash
# Fix the two bugs in rename.py
cat > /tmp/fixed_rename.py << 'PYEOF'
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

        # Extract date from filename - FIX 2: match exactly 8 digits
        match = re.search(r'(\d{8})', filename)
        if match:
            date_str = match.group(1)
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # Remove date from original name
            base, ext = os.path.splitext(filename)
            name_without_date = re.sub(r'_?\d{8}_?', '_', base).strip('_')
            new_name = f"{formatted_date}_{name_without_date}{ext}"

            # FIX 1: include directory in destination path
            os.rename(filepath, os.path.join(directory, new_name))
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
PYEOF
sudo tee /app/src/rename.py < /tmp/fixed_rename.py > /dev/null
sudo python3 /app/src/rename.py
