import os
import re

print("Script started.")

FRONTEND_DIR = 'frontend'

footer_links = '''
            <div style="margin-top: 8px;">
                <a href="/pages/privacy.html"><i class="fas fa-shield-alt"></i> Privacy Notice</a> |
                <a href="/pages/contact.html"><i class="fas fa-envelope"></i> Contact</a>
            </div>
'''

def update_file(filepath):
    print(f"Processing {filepath}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'href="/pages/privacy.html"' in content and 'href="/pages/contact.html"' in content:
        print(f"  Links already present, skipping.")
        return False
    
    # Look for <footer class="footer">
    footer_match = re.search(r'(<footer[^>]*class="footer"[^>]*>.*?)</footer>', content, re.DOTALL)
    if footer_match:
        footer_content = footer_match.group(1)
        if 'Privacy Notice' in footer_content or 'Contact</a>' in footer_content:
            print(f"  Footer already contains links, skipping.")
            return False
        # Insert before the last </div> inside footer
        last_div = footer_content.rfind('</div>')
        if last_div != -1:
            new_footer = footer_content[:last_div] + footer_links + footer_content[last_div:]
            new_content = content[:footer_match.start(1)] + new_footer + content[footer_match.end(1):]
        else:
            new_content = content[:footer_match.end(1)-8] + footer_links + content[footer_match.end(1)-8:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  Updated footer.")
        return True
    
    # Fallback: insert before </body>
    if '</body>' in content:
        if 'Privacy Notice' in content and 'Contact</a>' in content:
            print(f"  Links already present before </body>, skipping.")
            return False
        new_content = content.replace('</body>', footer_links + '\n</body>')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  Inserted before </body>.")
        return True
    
    print(f"  No suitable insertion point found.")
    return False

def main():
    if not os.path.isdir(FRONTEND_DIR):
        print(f"Frontend directory '{FRONTEND_DIR}' not found.")
        return
    
    html_files = []
    for root, dirs, files in os.walk(FRONTEND_DIR):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    print(f"Found {len(html_files)} HTML files.")
    updated = 0
    for filepath in html_files:
        if update_file(filepath):
            updated += 1
    
    print(f"Done. Updated {updated} files.")

if __name__ == '__main__':
    main()