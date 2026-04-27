import os
import re
import shutil
from datetime import datetime

# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------
def backup_file(filepath):
    """Create a backup with timestamp suffix."""
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{filepath}.backup_{timestamp}"
        shutil.copy2(filepath, backup_path)
        print(f"📦 Backup created: {backup_path}")

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# ------------------------------------------------------------------
# 1. Update app.py - add secure session config
# ------------------------------------------------------------------
def update_app_py():
    app_path = 'app.py'
    if not os.path.exists(app_path):
        print("❌ app.py not found in current directory")
        return False

    backup_file(app_path)
    content = read_file(app_path)

    # Check if config already added
    if 'SESSION_COOKIE_SECURE' in content:
        print("✅ app.py already has secure session config. Skipping.")
        return True

    # Add timedelta import if missing
    if 'from datetime import timedelta' not in content:
        # Find where other imports are (e.g., after 'from flask import ...')
        lines = content.split('\n')
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if not inserted and line.startswith('from flask import') or line.startswith('import '):
                new_lines.append('from datetime import timedelta')
                inserted = True
        if not inserted:
            # fallback: add at top
            new_lines.insert(0, 'from datetime import timedelta')
        content = '\n'.join(new_lines)

    # Find where app is created (after app = Flask(...))
    pattern = r'(app\s*=\s*Flask\([^)]+\))'
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        print("❌ Could not find 'app = Flask(...)' in app.py. Please add config manually.")
        return False

    # Build config block
    config_block = """
# Security cookie settings
app.config.update(
    SESSION_COOKIE_SECURE=True,           # Send session cookie only over HTTPS
    SESSION_COOKIE_HTTPONLY=True,         # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',        # Good CSRF protection
    PERMANENT_SESSION_LIFETIME=timedelta(days=31)  # Session expires after 31 days
)
"""
    # Insert after the app creation line
    insert_pos = match.end()
    content = content[:insert_pos] + "\n" + config_block + content[insert_pos:]

    write_file(app_path, content)
    print("✅ app.py updated with secure session config.")
    return True

# ------------------------------------------------------------------
# 2. Update auth.py - add session handling in login and logout
# ------------------------------------------------------------------
def update_auth_py():
    auth_path = 'backend/routes/auth.py'
    if not os.path.exists(auth_path):
        print("❌ auth.py not found at", auth_path)
        return False

    backup_file(auth_path)
    content = read_file(auth_path)

    # Add import for session if missing
    if 'from flask import session' not in content:
        # Find a line that already imports from flask (e.g., 'from flask import request, jsonify')
        lines = content.split('\n')
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if not inserted and 'from flask import' in line:
                # Add session to the existing import line
                if 'session' not in line:
                    new_line = re.sub(r'(from flask import [^\n]+)', r'\1, session', line)
                    new_lines[-1] = new_line
                inserted = True
        if not inserted:
            # Add import standalone
            new_lines.insert(0, 'from flask import session')
        content = '\n'.join(new_lines)

    # Add session code inside login route
    if 'session.permanent' not in content:
        # Find the login route function using a more robust regex
        # Look for "@auth_bp.route('/login'" and then the function definition
        login_pattern = r'(@auth_bp\.route\([\'"]/login[\'"],\s*methods=\[.*?\]\).*?def login\(\):.*?return jsonify\(.*?\))'
        match = re.search(login_pattern, content, re.DOTALL)
        if match:
            login_func = match.group(0)
            # Insert session setting after successful authentication (after db.commit or after user.last_login assignment)
            # We'll try to insert after the line that sets user.last_login
            new_login_func = login_func
            if 'db.session.commit()' in login_func:
                # Insert after the commit line (which is right before token generation)
                new_login_func = re.sub(
                    r'(db\.session\.commit\(\)\s*)\n',
                    r'\1\n    # Set session cookie\n    session.permanent = True\n    session["user_id"] = user.id\n    session["user_name"] = user.username\n\n',
                    login_func
                )
            elif 'user.last_login = datetime.utcnow()' in login_func:
                # Alternative pattern
                new_login_func = re.sub(
                    r'(user\.last_login = datetime\.utcnow\(\)\s*db\.session\.commit\(\))',
                    r'\1\n    \n    # Set session cookie\n    session.permanent = True\n    session["user_id"] = user.id\n    session["user_name"] = user.username',
                    login_func
                )
            else:
                # Fallback: insert before the line that creates access_token
                new_login_func = re.sub(
                    r'(access_token = create_access_token\(.*?\))',
                    r'    # Set session cookie\n    session.permanent = True\n    session["user_id"] = user.id\n    session["user_name"] = user.username\n\n    \1',
                    login_func
                )
            content = content.replace(login_func, new_login_func)

            # Add session.clear() in logout route
            # Find the logout route function
            logout_pattern = r'(@auth_bp\.route\([\'"]/logout[\'"],\s*methods=\[.*?\]\).*?def logout\(\):.*?return jsonify\(.*?\))'
            logout_match = re.search(logout_pattern, content, re.DOTALL)
            if logout_match:
                logout_func = logout_match.group(0)
                if 'session.clear()' not in logout_func:
                    # Insert session.clear() before the return statement
                    new_logout_func = re.sub(
                        r'(return jsonify\(.*?\))',
                        r'    session.clear()\n    \1',
                        logout_func
                    )
                    content = content.replace(logout_func, new_logout_func)
            write_file(auth_path, content)
            print("✅ auth.py updated with session handling.")
            return True
        else:
            print("⚠️  Could not locate login function in auth.py. Please add session code manually as shown in previous message.")
            return False
    else:
        print("✅ auth.py already has session handling. Skipping.")
        return True

# ------------------------------------------------------------------
# 3. (Optional) Add cookie consent banner to HTML files
# ------------------------------------------------------------------
def add_consent_banner():
    html_files = []
    for root, _, files in os.walk('frontend'):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))

    if not html_files:
        print("⚠️  No HTML files found in frontend/")
        return

    banner_html = '''
<div id="cookieBanner" style="display:none; position:fixed; bottom:0; left:0; right:0; background:#333; color:white; text-align:center; padding:1rem; z-index:9999;">
    This site uses cookies for essential functionality. By using this site, you accept our use of cookies.
    <button onclick="acceptCookies()" style="margin-left:1rem; background:#4CAF50; color:white; border:none; padding:0.5rem 1rem; cursor:pointer;">Accept</button>
</div>
<script>
    if (!localStorage.getItem('cookieConsent')) {
        document.getElementById('cookieBanner').style.display = 'block';
    }
    function acceptCookies() {
        localStorage.setItem('cookieConsent', 'true');
        document.getElementById('cookieBanner').style.display = 'none';
    }
</script>'''

    for filepath in html_files:
        backup_file(filepath)
        content = read_file(filepath)
        if 'cookieBanner' in content:
            print(f"⏩ {filepath} already has cookie banner.")
            continue
        # Insert before </body>
        if '</body>' in content:
            content = content.replace('</body>', banner_html + '\n</body>')
            write_file(filepath, content)
            print(f"✅ Added banner to {filepath}")
        else:
            print(f"⚠️  No </body> tag in {filepath}, skipping.")

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
if __name__ == '__main__':
    print("🔧 Starting cookie security setup...")
    update_app_py()
    update_auth_py()
    add_consent_banner()
    print("\n🎉 All done! Now commit and push changes, then redeploy on Render.")