import os
import re

# Define menus for each role
MENUS = {
    'admin': '''
<div class="sidebar-menu">
    <a href="admin-dashboard.html" class="sidebar-menu-item"><i class="fas fa-chalkboard"></i> Dashboard</a>
    <a href="admin-students.html" class="sidebar-menu-item"><i class="fas fa-users"></i> Students</a>
    <a href="admin-staff.html" class="sidebar-menu-item"><i class="fas fa-user-tie"></i> Staff</a>
    <a href="admin-programs.html" class="sidebar-menu-item"><i class="fas fa-book-open"></i> Programs</a>
    <a href="admin-modules.html" class="sidebar-menu-item"><i class="fas fa-layer-group"></i> Modules</a>
    <a href="admin-accommodation.html" class="sidebar-menu-item"><i class="fas fa-building"></i> Accommodation</a>
    <a href="admin-payments.html" class="sidebar-menu-item"><i class="fas fa-credit-card"></i> Payments</a>
    <a href="admin-tickets.html" class="sidebar-menu-item"><i class="fas fa-ticket-alt"></i> Tickets</a>
    <a href="admin-reports.html" class="sidebar-menu-item"><i class="fas fa-chart-line"></i> Reports</a>
    <a href="#" id="logoutLink" class="sidebar-menu-item"><i class="fas fa-sign-out-alt"></i> Logout</a>
</div>
''',
    'registrar': '''
<div class="sidebar-menu">
    <a href="registrar-dashboard.html" class="sidebar-menu-item"><i class="fas fa-chalkboard"></i> Dashboard</a>
    <a href="registrar-students.html" class="sidebar-menu-item"><i class="fas fa-users"></i> Students</a>
    <a href="registrar-registrations.html" class="sidebar-menu-item"><i class="fas fa-clipboard-list"></i> Semester Registrations</a>
    <a href="registrar-documents.html" class="sidebar-menu-item"><i class="fas fa-file-alt"></i> Documents</a>
    <a href="registrar-reports.html" class="sidebar-menu-item"><i class="fas fa-chart-line"></i> Reports</a>
    <a href="staff-queries.html" class="sidebar-menu-item"><i class="fas fa-question-circle"></i> Staff Queries</a>
    <a href="#" id="logoutLink" class="sidebar-menu-item"><i class="fas fa-sign-out-alt"></i> Logout</a>
</div>
''',
    'finance': '''
<div class="sidebar-menu">
    <a href="finance-dashboard.html" class="sidebar-menu-item"><i class="fas fa-chart-line"></i> Dashboard</a>
    <a href="admin-payments.html" class="sidebar-menu-item"><i class="fas fa-credit-card"></i> Payments</a>
    <a href="finance-reports.html" class="sidebar-menu-item"><i class="fas fa-chart-bar"></i> Reports</a>
    <a href="staff-queries.html" class="sidebar-menu-item"><i class="fas fa-question-circle"></i> Staff Queries</a>
    <a href="#" id="logoutLink" class="sidebar-menu-item"><i class="fas fa-sign-out-alt"></i> Logout</a>
</div>
''',
    'lecturer': '''
<div class="sidebar-menu">
    <a href="lecturer-dashboard.html" class="sidebar-menu-item"><i class="fas fa-chalkboard"></i> Dashboard</a>
    <a href="lecturer-courses.html" class="sidebar-menu-item"><i class="fas fa-book"></i> My Courses</a>
    <a href="lecturer-students.html" class="sidebar-menu-item"><i class="fas fa-users"></i> Students</a>
    <a href="lecturer-assignments.html" class="sidebar-menu-item"><i class="fas fa-tasks"></i> Assignments</a>
    <a href="staff-queries.html" class="sidebar-menu-item"><i class="fas fa-question-circle"></i> Queries</a>
    <a href="#" id="logoutLink" class="sidebar-menu-item"><i class="fas fa-sign-out-alt"></i> Logout</a>
</div>
''',
    'staff': '''
<div class="sidebar-menu">
    <a href="staff-dashboard.html" class="sidebar-menu-item"><i class="fas fa-chalkboard"></i> Dashboard</a>
    <a href="staff-queries.html" class="sidebar-menu-item"><i class="fas fa-question-circle"></i> Staff Queries</a>
    <a href="#" id="logoutLink" class="sidebar-menu-item"><i class="fas fa-sign-out-alt"></i> Logout</a>
</div>
'''
}

def detect_role(filepath):
    filename = os.path.basename(filepath).lower()
    if 'admin' in filename:
        return 'admin'
    if 'registrar' in filename:
        return 'registrar'
    if 'finance' in filename:
        return 'finance'
    if 'lecturer' in filename:
        return 'lecturer'
    if 'staff' in filename:
        return 'staff'
    return None

def fix_menu(filepath, menu_html):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    # Try to find the sidebar-menu div and replace its content
    pattern = r'(<div class="sidebar-menu">).*?(</div>)'
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, menu_html, content, flags=re.DOTALL)
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    else:
        # If no sidebar-menu div, try to insert it after the sidebar-header
        if '<div class="sidebar-header">' in content:
            new_content = content.replace('</div>', menu_html, 1)  # crude but works
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    return False

def main():
    count = 0
    for root, dirs, files in os.walk('frontend'):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                role = detect_role(filepath)
                if role and role in MENUS:
                    if fix_menu(filepath, MENUS[role]):
                        print(f'✅ Fixed menu in: {filepath}')
                        count += 1
                    else:
                        print(f'⚠️ Could not update menu in: {filepath}')
    print(f'🎉 Updated {count} files.')

if __name__ == '__main__':
    main()