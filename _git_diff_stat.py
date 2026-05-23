import subprocess, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
result = subprocess.run(['git', 'diff', '--stat'], capture_output=True, text=True)
sys.stdout.reconfigure(encoding='utf-8')
print(result.stdout)
if result.stderr:
    print('STDERR:', result.stderr, file=sys.stderr)
