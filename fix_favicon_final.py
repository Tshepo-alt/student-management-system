import os
import re

correct_block = '''    <link rel="icon" type="image/x-icon" href="/favicon/favicon.ico">
    <link rel="icon" type="image/png" sizes="96x96" href="/favicon/favicon-96x96.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/favicon/apple-touch-icon.png">
    <link rel="manifest" href="/favicon/site.webmanifest">
    <meta name="theme-color" content="#667eea">'''

pattern = r'<link[^>]*?href="[^"]*?favicon[^"]*?"[^>]*?>\s*|<link[^>]*?href="[^"]*?manifest[^"]*?"[^>]*?>\s*|<meta[^>]*?name="theme-color"[^>]*?>\s*'

for root, dirs, files in os.walk('frontend'):
    for file in files:
        if file.endswith('.html'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Remove all old favicon/manifest/theme-color lines
            new_content = re.sub(pattern, '', content, flags=re.IGNORECASE)
            # Insert correct block after <head>
            if '<head>' in new_content:
                new_content = new_content.replace('<head>', '<head>\n' + correct_block)
            else:
                new_content = '<head>\n' + correct_block + '\n</head>\n' + new_content
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f'✅ Fixed: {path}')
            else:
                print(f'⏭️ No changes: {path}')
print('🎉 Done.')