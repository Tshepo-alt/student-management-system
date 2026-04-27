import os
import re

replacements = [
    (r'["\']/pages/privacy\.html["\']', '"/privacy"'),
    (r'["\']privacy\.html["\']', '"/privacy"'),
    (r'["\']\.\./pages/privacy\.html["\']', '"/privacy"'),
    (r'["\']\.\./privacy\.html["\']', '"/privacy"'),
    (r'["\']/pages/contact\.html["\']', '"/contacts"'),
    (r'["\']contact\.html["\']', '"/contacts"'),
    (r'["\']\.\./pages/contact\.html["\']', '"/contacts"'),
    (r'["\']\.\./contact\.html["\']', '"/contacts"'),
    (r'["\']/pages/contacts\.html["\']', '"/contacts"'),
    (r'["\']contacts\.html["\']', '"/contacts"'),
    (r'["\']/pages/terms\.html["\']', '"/terms"'),
    (r'["\']terms\.html["\']', '"/terms"'),
    (r'["\']\.\./pages/terms\.html["\']', '"/terms"'),
    (r'["\']\.\./terms\.html["\']', '"/terms"'),
    (r'["\']/pages/about\.html["\']', '"/about"'),
    (r'["\']about\.html["\']', '"/about"'),
    (r'["\']\.\./pages/about\.html["\']', '"/about"'),
    (r'["\']\.\./about\.html["\']', '"/about"'),
]

def update_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = content
        for pattern, repl in replacements:
            new_content = re.sub(pattern, repl, new_content)
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Updated: {filepath}")
            return True
        else:
            print(f"⏭️  No changes: {filepath}")
            return False
    except Exception as e:
        print(f"❌ Error {filepath}: {e}")
        return False

def main():
    base = 'frontend'
    if not os.path.isdir(base):
        print(f"❌ Folder '{base}' not found – are you in the project root?")
        return

    html_files = []
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.endswith('.html'):
                full = os.path.join(root, f)
                html_files.append(full)

    if not html_files:
        print(f"No .html files found under '{base}'")
        return

    print(f"Found {len(html_files)} HTML files")
    updated = 0
    for fp in html_files:
        if update_file(fp):
            updated += 1
    print(f"\n✅ Updated {updated} files.")

if __name__ == '__main__':
    main()