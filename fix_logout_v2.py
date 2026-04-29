import os
import re

NEW_LOGOUT_SCRIPT = '''
<script>
(function() {
    function doLogout(e) {
        if (e) e.preventDefault();
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = 'login.html';
    }
    const logoutElements = document.querySelectorAll('#logoutLink, .logout-link, .logout-btn, [data-logout]');
    logoutElements.forEach(el => el.addEventListener('click', doLogout));
    window.logout = doLogout;
})();
</script>
'''

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove any existing script blocks that contain localStorage.clear or /api/auth/logout
    # Use a more aggressive removal
    content = re.sub(r'<script[^>]*>[\s\S]*?(?:localStorage\.clear|/api/auth/logout|sessionStorage\.clear)[\s\S]*?</script>', '', content, flags=re.IGNORECASE)
    
    # If our new script is not already present, insert it before </body>
    if '</body>' in content and NEW_LOGOUT_SCRIPT.strip() not in content:
        content = content.replace('</body>', NEW_LOGOUT_SCRIPT + '\n</body>')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    count = 0
    scanned = 0
    for root, dirs, files in os.walk('frontend'):
        for file in files:
            if file.endswith('.html'):
                scanned += 1
                path = os.path.join(root, file)
                if process_file(path):
                    print(f'✅ Updated: {path}')
                    count += 1
                else:
                    print(f'⏭️  Skipped (no change): {path}')
    print(f'Scanned {scanned} HTML files. Updated {count} files with logout script.')
    print('Done.')

if __name__ == '__main__':
    main()