import os
import re

# Directories to scan (add more if needed)
SCAN_DIRS = ['frontend', 'backend/routes']  # adjust as needed
# File extensions to check
EXTENSIONS = ('.html', '.js', '.py', '.txt', '.css')

# Patterns to search for
PATTERNS = [
    r'["\']/pages/index\.html["\']',      # "/pages/index.html"
    r'["\']\.\./index\.html["\']',        # "../index.html"
    r'["\']\.\./\.\./index\.html["\']',   # "../../index.html"
    r'["\']pages/index\.html["\']',       # "pages/index.html" (relative)
]

def scan_file(filepath):
    found = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            for pattern in PATTERNS:
                matches = re.findall(pattern, content)
                if matches:
                    found.extend(matches)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return found

def main():
    total_files = 0
    files_with_issues = 0
    root = os.path.dirname(__file__)

    for scan_dir in SCAN_DIRS:
        full_path = os.path.join(root, scan_dir)
        if not os.path.isdir(full_path):
            print(f"Directory not found: {full_path}")
            continue

        for root_dir, dirs, files in os.walk(full_path):
            for file in files:
                if file.endswith(EXTENSIONS):
                    total_files += 1
                    filepath = os.path.join(root_dir, file)
                    matches = scan_file(filepath)
                    if matches:
                        files_with_issues += 1
                        rel_path = os.path.relpath(filepath, root)
                        print(f"\n{rel_path}:")
                        for match in matches:
                            print(f"  -> found: {match}")

    print(f"\nSummary: Scanned {total_files} files. Found old index references in {files_with_issues} file(s).")

if __name__ == '__main__':
    main()