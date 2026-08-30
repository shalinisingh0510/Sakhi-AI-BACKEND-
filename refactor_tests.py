import os
import re
from pathlib import Path

tests_dir = Path("tests")

def refactor_test_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    
    # Replace build_client(database_path: Path) -> TestClient:
    content = re.sub(r'def build_client\(database_path: Path\)\s*->\s*TestClient:', 
                     'def build_client(database_url: str) -> TestClient:', content)
    
    # Replace build_service(database_path: Path) -> ...:
    content = re.sub(r'def build_service\(database_path: Path\)(.*?):', 
                     r'def build_service(database_url: str)\1:', content)
                     
    # Replace settings = Settings(database_path=database_path)
    content = re.sub(r'Settings\(database_path=database_path\)', 
                     'Settings(database_url=database_url)', content)
                     
    # Replace tmp_path / "foo.sqlite3" with test_db_url
    content = re.sub(r'build_client\(tmp_path\s*/\s*"[^"]+"\)', 'build_client(test_db_url)', content)
    content = re.sub(r'build_service\(tmp_path\s*/\s*"[^"]+"\)', 'build_service(test_db_url)', content)
    
    # Some use database_path = tmp_path / "foo.sqlite3" ... build_client(database_path)
    # We can replace the assignment of database_path
    content = re.sub(r'database_path\s*=\s*tmp_path\s*/\s*"[^"]+"', 'database_path = test_db_url', content)
    
    file_path.write_text(content, encoding="utf-8")

for root, _, files in os.walk(tests_dir):
    for f in files:
        if f.endswith(".py"):
            refactor_test_file(Path(root) / f)
            
print("Refactored test files.")

