content = open('AppMonitor.spec', encoding='utf-8').read()
idx = content.find("name='AppMonitor'")
if idx >= 0:
    print(f"FOUND at {idx}: '{content[idx:idx+30]}'")
else:
    print("NOT FOUND")
    # Покажем что вокруг name=
    idx2 = content.find("name=")
    if idx2 >= 0:
        print(f"name= found at {idx2}: '{content[idx2:idx2+40]}'")
    else:
        print("name= also NOT FOUND")
