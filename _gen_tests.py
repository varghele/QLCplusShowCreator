import os, base64

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "unit")

def w(name, content):
    p = os.path.join(BASE, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Written {name} ({len(content)} bytes)")

print("Writing test files to:", BASE)

