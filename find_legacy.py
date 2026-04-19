
with open(r'c:\Users\Matia\OneDrive\Escritorio\prueba-ia-evolutia\caloria_tracker\index.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'renderLoginPage' in line or 'showUserSelect' in line or 'pinBuffer' in line:
            print(f"{i+1}: {line.strip()}")
