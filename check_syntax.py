
with open(r'c:\Users\Matia\OneDrive\Escritorio\prueba-ia-evolutia\caloria_tracker\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)

for i, script in enumerate(scripts):
    open_p = script.count('('); close_p = script.count(')')
    open_b = script.count('{'); close_b = script.count('}')
    open_s = script.count('['); close_s = script.count(']')
    
    print(f"Script {i}:")
    print(f"  Parentheses: {open_p} vs {close_p}")
    print(f"  Braces: {open_b} vs {close_b}")
    print(f"  Brackets: {open_s} vs {close_s}")

    if open_b != close_b:
        lines = script.split('\n')
        balance = 0
        for ln, line in enumerate(lines):
            balance += line.count('{') - line.count('}')
            if balance < 0:
                print(f"  CRITICAL: Negative brace balance at line {ln+1}: {line}")
                break
