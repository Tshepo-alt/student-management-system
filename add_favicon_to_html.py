import os
import re

# The HTML snippet to insert inside <head>
FAVICON_HTML = '''
    <!-- Favicon -->
    <link rel="icon" type="image/x-icon" href="/favicon/favicon.ico">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/favicon/apple-touch-icon.png">
    <link rel="manifest" href="/favicon/site.webmanifest">
'''

# Indicator that the links are already present (to avoid duplication)
CHECK_STRING = '/favicon/favicon.ico'

def add_favicon_to_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if already has our favicon
    if CHECK_STRING in content:
        print(f"Skipping {filepath} – favicon already present")
        return False

    # Find the <head> tag and insert after it or before </head>
    head_match = re.search(r'<head[^>]*>', content, re.IGNORECASE)
    if not head_match:
        print(f"Warning: No <head> tag found in {filepath}")
        return False

    head_end = head_match.end()
    # Insert after the opening <head> tag (with proper indentation attempt)
    new_content = content[:head_end] + FAVICON_HTML + content[head_end:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Updated {filepath}")
    return True

def main():
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    if not os.path.isdir(frontend_dir):
        print("Error: frontend directory not found. Run this script from the project root.")
        return

    count = 0
    for root, dirs, files in os.walk(frontend_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                if add_favicon_to_html(filepath):
                    count += 1

    print(f"\nDone. Updated {count} HTML files.")

if __name__ == '__main__':
    main()