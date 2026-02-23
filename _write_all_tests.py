#!/usr/bin/env python3
import os

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "unit")

def w(name, content):
    with open(os.path.join(BASE, name), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Written {name}")

print("Writing test files to:", BASE)
