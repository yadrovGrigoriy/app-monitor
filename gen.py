import os
base = r"C:/Users/Григорий/code/AppMonitor"

files = {}

files["requirements.txt"] = """PyQt5>=5.15
pywin32>=306
schedule>=1.2
"""

with open(os.path.join(base, "generate2.py"), "w", encoding="utf-8") as f:
    f.write("
".join(code))
print("OK")