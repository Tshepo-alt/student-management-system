import os
import re

def update_home_links(directory='frontend'):
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Replace href="/index.html" with href="/"
                new_content = re.sub(r'href=["\']/index\.html["\']', 'href="/"', content)
                # Also replace href="index.html" (if relative) – be careful not to break other things
                new_content = re.sub(r'href=["\']index\.html["\']', 'href="/"', new_content)
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Updated {path}")
                    count += 1
    print(f"Updated {count} files.")

if __name__ == '__main__':
    update_home_links()