import os
import re

# Define allowed roles for each page (exact filename or pattern)
def get_allowed_roles(filename):
    # Exact matches
    exact_map = {
        'admin-dashboard.html': ['admin', 'administrator'],
        'admin-students.html': ['admin', 'administrator'],
        'admin-programs.html': ['admin', 'administrator'],
        'admin-modules.html': ['admin', 'administrator'],
        'admin-payments.html': ['admin', 'administrator'],
        'admin-accommodation.html': ['admin', 'administrator'],
        'admin-reports.html': ['admin', 'administrator'],
        'admin-settings.html': ['admin', 'administrator'],
        'admin-staff.html': ['admin', 'administrator'],
        'admin-tickets.html': ['admin', 'administrator'],
        'registrar-dashboard.html': ['registrar'],
        'registrar-students.html': ['registrar'],
        'registrar-documents.html': ['registrar'],
        'registrar-reports.html': ['registrar'],
        'registrar-registrations.html': ['registrar'],
        'finance-dashboard.html': ['finance'],
        'finance-records.html': ['finance'],
        'lecturer-dashboard.html': ['lecturer'],
        'staff-dashboard.html': ['staff'],
        'student-dashboard.html': ['student'],
        'alumni-dashboard.html': ['alumni'],
    }
    if filename in exact_map:
        return exact_map[filename]
    # Prefix rules
    if filename.startswith('admin-'):
        return ['admin', 'administrator']
    if filename.startswith('registrar-'):
        return ['registrar']
    if filename.startswith('finance-'):
        return ['finance']
    if filename.startswith('lecturer-'):
        return ['lecturer']
    if filename.startswith('staff-'):
        return ['staff']
    if filename.startswith('student-'):
        return ['student']
    if filename.startswith('alumni-'):
        return ['alumni']
    # Public pages (no login required, or accessible to all logged‑in users)
    public_pages = ['login.html', 'register.html', 'forgot-password.html', 'reset-password.html',
                    'index.html', 'privacy.html', 'contacts.html', 'terms.html', 'about.html',
                    'chatbot.html', 'accomodation.html', 'assignments.html', 'results-view.html',
                    'student-timetables.html', 'student-queries.html', 'student-profile.html',
                    'student-exam-registration.html', 'course-registration.html', 'application-status.html',
                    'semester-registration.html', 'campus-selection.html', 'registration-waiting.html']
    if filename in public_pages:
        return []   # No role restriction (but token may be checked separately)
    # Default: only student (fallback)
    return ['student']

def inject_role_check(filepath, allowed_roles):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Remove any existing role‑check scripts
    content = re.sub(r'<script[^>]*>[\s\S]*?// ========== ROLE CHECK ==========[\s\S]*?</script>', '', content)
    content = re.sub(r'<script[^>]*>[\s\S]*?if \(!allowedRoles\.includes\(userRole\)\)[\s\S]*?</script>', '', content)

    if allowed_roles is None:
        role_script = ''
    else:
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
    if (allowedRoles.length > 0 && !allowedRoles.includes(userRole)) {{
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
    # Insert right after the opening <body> tag
    body_match = re.search(r'<body[^>]*>', content, re.IGNORECASE)
    if body_match:
        insert_pos = body_match.end()
        content = content[:insert_pos] + '\n' + role_script + content[insert_pos:]
    else:
        # Fallback: insert before </head>
        content = content.replace('</head>', role_script + '</head>')

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'✅ Updated: {filepath}')

def main():
    for root, dirs, files in os.walk('frontend'):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                allowed = get_allowed_roles(file)
                inject_role_check(filepath, allowed)
    print('🎉 All HTML files updated with improved role checks.')

if __name__ == '__main__':
    main()