import os, json
base = "C:/Users/Григорий/code/AppMonitor"
json_path = os.path.join(base, "project_files.json")
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)
data["test"] = "hello"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print("OK")
