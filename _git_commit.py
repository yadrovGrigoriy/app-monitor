import subprocess, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Add all changes
subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)

# Commit
result = subprocess.run(
    ['git', 'commit', '-m', 'feat: major refactoring of core, UI and tests\n\n- Refactored core/database.py: improved DB layer structure\n- Refactored ui/: main_window, styles, dialogs, widgets\n- Refactored tests: consolidated test structure\n- Updated api/: server and schemas improvements\n- Updated client/main.py\n- Added AGENTS.md, LICENSE.txt\n- Added build scripts and installer\n- Added role_manager.py\n- Removed unused test files'],
    capture_output=True, text=True
)
sys.stdout.reconfigure(encoding='utf-8')
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr, file=sys.stderr)
print('RC:', result.returncode)
