import os
import re
from pathlib import Path

tests_dir = Path("tests")

def fix_test_db_url_fixture(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    
    # Any def test_*(...): that contains 'test_db_url' but doesn't have it in the signature
    # Needs to be updated.
    
    lines = content.split('\n')
    new_lines = []
    
    in_test_func = False
    func_start_idx = -1
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.startswith('def test_'):
            in_test_func = True
            func_start_idx = i
            
    # Simpler regex approach:
    # Find all test function definitions. If the body contains test_db_url, make sure it's in the args.
    
    def replacement(match):
        sig = match.group(1)
        if 'test_db_url' not in sig:
            if sig.endswith(')'):
                sig = sig[:-1]
                if sig.endswith('('):
                    return f"def test_{match.group(2)}({sig}test_db_url: str):"
                else:
                    return f"def test_{match.group(2)}({sig}, test_db_url: str):"
        return match.group(0)
    
    # Wait, we need to only add it if the function body uses it.
    # It's safer to just add it to ALL test_ functions that use it.
    
    blocks = re.split(r'(^def test_[^\(]+)', content, flags=re.MULTILINE)
    new_content = blocks[0]
    for i in range(1, len(blocks), 2):
        func_def_start = blocks[i]
        rest = blocks[i+1]
        
        # Extract signature
        sig_match = re.match(r'(\(.*?\)\s*(?:->\s*[^:]+)?\s*:)', rest, flags=re.DOTALL)
        if sig_match:
            sig = sig_match.group(1)
            body = rest[len(sig):]
            if 'test_db_url' in body and 'test_db_url' not in sig:
                # Add test_db_url to signature
                # Find the closing paren
                paren_idx = sig.rfind(')')
                if paren_idx != -1:
                    before_paren = sig[:paren_idx].strip()
                    after_paren = sig[paren_idx:]
                    if before_paren.endswith('('):
                        new_sig = before_paren + "test_db_url: str" + after_paren
                    else:
                        new_sig = before_paren + ", test_db_url: str" + after_paren
                    new_content += func_def_start + new_sig + body
                else:
                    new_content += func_def_start + rest
            else:
                new_content += func_def_start + rest
        else:
            new_content += func_def_start + rest

    file_path.write_text(new_content, encoding="utf-8")

for root, _, files in os.walk(tests_dir):
    for f in files:
        if f.endswith(".py"):
            fix_test_db_url_fixture(Path(root) / f)
            
print("Injected test_db_url fixture.")

