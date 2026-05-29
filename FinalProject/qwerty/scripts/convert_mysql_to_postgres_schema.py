import re
from pathlib import Path

source = Path('database/schema_mysql.sql').read_text()

out = source
out = re.sub(r'SET FOREIGN_KEY_CHECKS = 0;\s*', '', out)
out = re.sub(r'SET FOREIGN_KEY_CHECKS = 1;', '', out)
out = out.replace('`', '"')
out = re.sub(r'\)\s*ENGINE=InnoDB(?:\s*COMMENT=.*?)?;', ');', out, flags=re.S)
out = re.sub(r'\bTINYINT\b', 'SMALLINT', out)
out = re.sub(r'\bDATETIME\b', 'TIMESTAMP', out)
out = re.sub(r'\bINT AUTO_INCREMENT PRIMARY KEY\b', 'SERIAL PRIMARY KEY', out)
out = re.sub(r'\bINT AUTO_INCREMENT\b', 'SERIAL', out)
out = re.sub(r'\bDECIMAL\((\d+),(\d+)\)\b', r'NUMERIC(\1,\2)', out)
out = re.sub(r'\bUNIQUE KEY\s+\w+\s*\(', 'UNIQUE (', out)
out = re.sub(r'\bON UPDATE CURRENT_TIMESTAMP\b', '', out)
out = re.sub(r'COMMENT \'[^\']*\'', '', out)
out = re.sub(r'\s*INDEX\s+[^\(]*\([^\)]*\),?\s*\n', '\n', out)
out = re.sub(r'\bENUM\([^\)]*\)', 'VARCHAR(255)', out)
out = re.sub(r'\bDEFAULT CURRENT_TIMESTAMP\b', 'DEFAULT CURRENT_TIMESTAMP', out)
out = re.sub(r',\s*\)', ')', out)
out = re.sub(r'\bUNIQUE\s*\(\s*\)\s*,?', '', out)

output_path = Path('supabase/schemas/initial_schema.sql')
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(out)
print(f'Wrote {output_path}')
