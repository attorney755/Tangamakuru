import re

with open('app/__init__.py', 'r') as f:
    content = f.read()

# Find where to add the reports import
lines = content.split('\n')
new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    if 'app.register_blueprint(auth_bp, url_prefix=\'/auth\')' in line:
        # Add reports blueprint after auth
        new_lines.append('')
        new_lines.append('# Import models for Flask-Migrate')
        new_lines.append('from . import models')
        new_lines.append('')
        new_lines.append('# Register reports blueprint')
        new_lines.append('from .routes.reports import reports_bp')
        new_lines.append('app.register_blueprint(reports_bp, url_prefix=\'/reports\')')
        new_lines.append('')

with open('app/__init__.py', 'w') as f:
    f.write('\n'.join(new_lines))

print("Updated app/__init__.py")
