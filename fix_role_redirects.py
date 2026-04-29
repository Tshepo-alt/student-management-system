import os
import re

# Map filename patterns to allowed roles
role_map = {
    'admin-dashboard': ['admin', 'administrator'],
    'admin-': ['admin', 'administrator'],
    'finance-dashboard': ['finance'],
    'finance-': ['finance'],
    'lecturer-dashboard': ['lecturer'],
    'lecturer-': ['lecturer'],
    'registrar-dashboard': ['registrar'],
    'registrar-': ['registrar'],
    'staff-dashboard': ['staff'],
    'staff-': ['staff'],
    'student-dashboard': ['student'],
    'student-': ['student'],
    'alumni-dashboard': ['alumni'],
    'alumni-': ['alumni'],
    # Public pages (no restrictions)
    'login.html': [],
    'register.html': [],
    'forgot-password.html': [],
    'reset-password.html': [],
    'index.html': [],
    'privacy.html': [],
    'contacts.html': [],
    'terms.html': [],
    'about.html': [],
    'chatbot.html': [],
    'accomodation.html': [],
    'assignments.html': [],
    'results-view.html': [],
    'student-timetables.html': [],
    'student-queries.html': [],
    'student-profile.html': [],
    'student-exam-registration.html': [],
    'course-registration.html': [],
    'application-status.html': [],
    'semester-registration.html': [],
}

def allowed_roles_for_file(filename):
    for pattern, roles in role_map.items():
        if pattern in filename:
            return roles
    return None  # means role check not required (but public)

def inject_role_check(filepath, allowed_roles):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove any existing role check script (to avoid duplication)
    pattern = r'<script[^>]*>[\s\S]*?// ========== ROLE CHECK ==========[\s\S]*?</script>'
    content = re.sub(pattern, '', content)
    
    if allowed_roles is None or allowed_roles == []:
        # Public page – only check token, no role restriction
        role_script = '''
<script>
// ========== ROLE CHECK (PUBLIC) ==========
(function() {
    const token = localStorage.getItem('access_token');
    const userRole = (JSON.parse(localStorage.getItem('user') || '{}')).role || localStorage.getItem('user_role');
    // If logged in, stay; if not, allow access.
})();
</script>
'''
    else:
        # Restricted page
        roles_js = allowed_roles
        role_script = f'''
<script>
// ========== ROLE CHECK ==========
(function() {{
    const token = localStorage.getItem('access_token');
    const user = JSON.parse(localStorage.getItem('user') || '{{}}');
    const userRole = user.role || localStorage.getItem('user_role');
    if (!token) {{
        window.location.href = 'login.html';
        return;
    }}
    const allowedRoles = {roles_js};
    if (!allowedRoles.includes(userRole)) {{
        // Redirect to the appropriate dashboard
        const roleRedirects = {{
            'admin': 'admin-dashboard.html',
            'administrator': 'admin-dashboard.html',
            'registrar': 'registrar-dashboard.html',
            'finance': 'finance-dashboard.html',
            'lecturer': 'lecturer-dashboard.html',
            'staff': 'staff-dashboard.html',
            'student': 'student-dashboard.html',
            'alumni': 'alumni-dashboard.html'
        }};
        const target = roleRedirects[userRole] || 'student-dashboard.html';
        window.location.href = target;
        return;
    }}
}})();
</script>
'''
    # Insert before </body>
    content = content.replace('</body>', role_script + '\n</body>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'✅ Updated: {filepath}')

def main():
    for root, dirs, files in os.walk('frontend'):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                roles = allowed_roles_for_file(file)
                inject_role_check(filepath, roles)
    print('🎉 All HTML files updated with role checks.')

if __name__ == '__main__':
    main()