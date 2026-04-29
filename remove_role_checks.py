import os
import re

def remove_role_scripts(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Pattern to match script blocks that contain "roleRedirects" or "// ========== ROLE CHECK =========="
    pattern = r'<script[^>]*>[\s\S]*?(?:roleRedirects|// ========== ROLE CHECK ==========)[\s\S]*?</script>'
    new_content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    count = 0
    for root, dirs, files in os.walk('frontend'):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                if remove_role_scripts(path):
                    print(f'✅ Cleaned: {path}')
                    count += 1
    print(f'🎉 Removed role‑check scripts from {count} files.')

if __name__ == '__main__':
    main()