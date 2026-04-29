import os
import re

# Define the sidebar menu HTML for each role
SIDEBAR_MENUS = {
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
    """Determine role based on the filename in the path."""
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

def inject_sidebar(filepath, menu_html):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Look for a <div class="sidebar-menu"> container and replace its content
    # If not found, try to insert after the sidebar-header
    new_content = content
    pattern = r'(<div class="sidebar-menu">).*?(</div>)'
    if re.search(pattern, new_content, re.DOTALL):
        new_content = re.sub(pattern, menu_html, new_content, flags=re.DOTALL)
    elif '<div class="sidebar-header">' in new_content:
        # Insert after the sidebar-header div
        new_content = new_content.replace('</div>', menu_html, 1)
    else:
        return False

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
                filepath = os.path.join(root, file)
                role = detect_role(filepath)
                if role and role in SIDEBAR_MENUS:
                    if inject_sidebar(filepath, SIDEBAR_MENUS[role]):
                        print(f'✅ Updated sidebar in: {filepath}')
                        count += 1
                    else:
                        print(f'⚠️ Could not update: {filepath} (no sidebar container found)')
    print(f'🎉 Updated {count} files.')

if __name__ == '__main__':
    main()