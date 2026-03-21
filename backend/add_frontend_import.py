import re

with open('app/__init__.py', 'r') as f:
    content = f.read()

lines = content.split('\n')
new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    if 'app.register_blueprint(reports_bp, url_prefix' in line:
        # Add frontend blueprint after reports
        new_lines.append('')
        new_lines.append('    # Register frontend blueprint')
        new_lines.append('    from .routes.frontend import frontend_bp')
        new_lines.append('    app.register_blueprint(frontend_bp)')

with open('app/__init__.py', 'w') as f:
    f.write('\n'.join(new_lines))

print("Added frontend blueprint")
