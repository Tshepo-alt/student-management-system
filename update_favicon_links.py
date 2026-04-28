import os
import re

old_links = [
    r'<link rel="icon" type="image/x-icon" href="/favicon/favicon\.ico">',
    r'<link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16\.png">',
    r'<link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32\.png">',
    r'<link rel="apple-touch-icon" sizes="180x180" href="/favicon/apple-touch-icon\.png">',
    r'<link rel="manifest" href="/favicon/site\.webmanifest">'
]

new_links = '''    <link rel="apple-touch-icon" sizes="180x180" href="/favicon/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16.png">
    <link rel="manifest" href="/favicon/site.webmanifest">
    <link rel="mask-icon" href="/favicon/safari-pinned-tab.svg" color="#667eea">
    <meta name="msapplication-TileColor" content="#667eea">
    <meta name="theme-color" content="#667eea">'''

for root, dirs, files in os.walk('frontend'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Remove old favicon lines
            new_content = content
            for old in old_links:
                new_content = re.sub(old, '', new_content)
            # Insert new block after <meta charset... or at beginning of head
            # We'll insert right after the first <meta charset line
            pattern = r'(<head>.*?<meta charset="[^"]*".*?>)'
            if re.search(pattern, new_content, re.DOTALL):
                new_content = re.sub(pattern, r'\1\n' + new_links, new_content, flags=re.DOTALL)
            else:
                # fallback: insert after <head>
                new_content = new_content.replace('<head>', '<head>\n' + new_links)
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'✅ Updated {path}')
            else:
                print(f'⏭️ No changes in {path}')

print("Script finished.")