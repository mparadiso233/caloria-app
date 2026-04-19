
with open(r'c:\Users\Matia\OneDrive\Escritorio\prueba-ia-evolutia\caloria_tracker\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Only analyze inside <script> tags
import re
scripts = re.findall(r'<script>(.*?)</script>', content, re.DOTALL)

for i, script in enumerate(scripts):
    open_p = script.count('(')
    close_p = script.count(')')
    open_b = script.count('{')
    close_b = script.count('}')
    open_s = script.count('[')
    close_s = script.count(']')
    
    print(f"Script {i}:")
    print(f"  Parentheses: {open_p} ( vs {close_p} ) -> {'OK' if open_p == close_p else 'FAIL'}")
    print(f"  Braces: {open_b} {{ vs {close_b} }} -> {'OK' if open_b == close_b else 'FAIL'}")
    print(f"  Brackets: {open_s} [ vs {close_s} ] -> {'OK' if open_s == close_s else 'FAIL'}")

    if open_b != close_b:
        # Find where it might be broken
        lines = script.split('\n')
        balance = 0
        for ln, line in enumerate(lines):
            balance += line.count('{') - line.count('}')
            if balance < 0:
                print(f"  First negative balance at line {ln+1}: {line}")
                break
