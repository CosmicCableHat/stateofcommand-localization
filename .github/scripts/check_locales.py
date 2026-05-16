import os
import re
import sys
import subprocess
from collections import Counter

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        
    locales_dir = 'locales'
    en_file = os.path.join(locales_dir, 'en.txt')
    
    if not os.path.exists(en_file):
        print(f"Error: Base locale file {en_file} not found")
        sys.exit(1)

    # Token regex to match %d, %s, %.1f, %zu, %%, %.0f
    token_regex = re.compile(r'%(?:\.\d+)?[a-zA-Z]+|%%')
    
    en_data = {}
    
    with open(en_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            
            key, value = line.split('=', 1)
            key = key.strip()
            tokens = token_regex.findall(value)
            en_data[key] = {
                'line': line_num,
                'tokens': tokens,
                'value': value.strip()
            }

    errors_found = False

    # Fetch origin main to ensure it is available for comparison
    if 'GITHUB_ACTIONS' in os.environ:
        subprocess.run(['git', 'fetch', 'origin', 'main'], capture_output=True)

    for filename in os.listdir(locales_dir):
        if not filename.endswith('.txt') or filename == 'en.txt':
            continue
            
        filepath = os.path.join(locales_dir, filename)
        
        # Check if this is a new file
        res = subprocess.run(['git', 'ls-tree', '-r', 'origin/main', filepath], capture_output=True, text=True)
        is_new_file = (res.returncode != 0 or not res.stdout.strip())
        
        translated_keys = 0
        total_valid_keys = 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            msg = "File is not valid UTF-8 encoded."
            print(f"::error file={filepath}::{msg}")
            errors_found = True
            continue

        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=' not in line:
                msg = "Invalid format, missing '=', only edit values after '='"
                print(f"::error file={filepath},line={line_num}::{msg}")
                errors_found = True
                continue
                
            key, value = line.split('=', 1)
            
            if value.startswith(' '):
                msg = "No spaces allowed between '=' and the translated text"
                print(f"::error file={filepath},line={line_num}::{msg}")
                errors_found = True
                continue
                
            key = key.strip()
            
            if key not in en_data:
                msg = f"Unknown key '{key}', do NOT modify the key names on the left side"
                print(f"::error file={filepath},line={line_num}::{msg}")
                errors_found = True
                continue
                
            total_valid_keys += 1
            if value.strip() != en_data[key]['value']:
                translated_keys += 1
                
            loc_tokens = token_regex.findall(value)
            en_tokens = en_data[key]['tokens']
            
            if Counter(loc_tokens) != Counter(en_tokens):
                msg = f"Formatting tokens mismatch for key '{key}', expected `{en_tokens}`, found `{loc_tokens}`"
                print(f"::error file={filepath},line={line_num}::{msg.replace('`', '')}")
                errors_found = True

        if is_new_file and total_valid_keys > 0:
            ratio = translated_keys / len(en_data)
            if ratio < 0.5:
                msg = f"New file must be at least 50% translated (currently {ratio:.1%}, needs {len(en_data)/2:.0f} keys)"
                print(f"::error file={filepath}::{msg}")
                errors_found = True

    if errors_found:
        print("\nCheck failed, please fix the errors above")
        sys.exit(1)
    else:
        print("\nAll locale files passed the check successfully")
        sys.exit(0)

if __name__ == '__main__':
    main()