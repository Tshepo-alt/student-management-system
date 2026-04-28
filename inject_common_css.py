import os
import re

def inject_css_and_meta():
    # Path to your common CSS file (relative to web root)
    css_link = '<link rel="stylesheet" href="/css/portal-common.css">'
    viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes, viewport-fit=cover">'
    
    # Counters
    updated = 0
    skipped = 0
    
    for root, dirs, files in os.walk('frontend'):
        for file in files:
            if not file.endswith('.html'):
                continue
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            modified = False
            
            # 1. Ensure viewport meta is present
            if not re.search(r'<meta\s+name="viewport"', content, re.IGNORECASE):
                # Insert after <head> or after charset meta
                pattern = r'<head[^>]*>'
                if re.search(pattern, content, re.IGNORECASE):
                    content = re.sub(pattern, r'\g<0>\n    ' + viewport_meta, content, flags=re.IGNORECASE)
                    modified = True
                elif '<head>' in content:
                    content = content.replace('<head>', '<head>\n    ' + viewport_meta)
                    modified = True
            
            # 2. Inject common CSS link if not already present
            if '/css/portal-common.css' not in content:
                # Insert before </head>
                content = content.replace('</head>', f'    {css_link}\n</head>')
                modified = True
            
            if modified:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f'✅ Updated: {filepath}')
                updated += 1
            else:
                print(f'⏭️  Already OK: {filepath}')
                skipped += 1
    
    print(f'\n🎉 Done. Updated {updated} files, skipped {skipped}.')

if __name__ == '__main__':
    inject_css_and_meta()