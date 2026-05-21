import os, json
base = "C:/Users/Григорий/code/AppMonitor"
json_path = os.path.join(base, "project_files.json")
data = {}

# requirements.txt
data["requirements.txt"] = "PyQt5>=5.15
pywin32>=306
schedule>=1.2
"

data["core/__init__.py"] = ""
data["ui/__init__.py"] = ""

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print("OK")