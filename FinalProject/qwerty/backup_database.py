"""Backup MySQL database"""
import pymysql
import os
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Update if you have a password
    'database': 'qwerty',
    'charset': 'utf8mb4'
}

def backup_database():
    """Create a backup of the MySQL database"""
    try:
        # Create backups directory if it doesn't exist
        backup_dir = 'database/backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'qwerty_backup_{timestamp}.sql')
        
        print(f"📦 Creating backup of database 'qwerty'...")
        print(f"📁 Backup file: {backup_file}")
        
        # Connect to MySQL
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            print("⚠️  No tables found in database")
            return False
        
        print(f"📊 Found {len(tables)} tables: {', '.join(tables)}")
        
        # Open backup file for writing
        with open(backup_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write(f"-- MySQL Database Backup\n")
            f.write(f"-- Database: qwerty\n")
            f.write(f"-- Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"-- Tables: {', '.join(tables)}\n\n")
            f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")
            
            # Backup each table
            for i, table in enumerate(tables, 1):
                print(f"  [{i}/{len(tables)}] Backing up table '{table}'...")
                
                # Get CREATE TABLE statement
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_table = cursor.fetchone()[1]
                
                f.write(f"-- Table: {table}\n")
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                f.write(f"{create_table};\n\n")
                
                # Get table data
                cursor.execute(f"SELECT * FROM `{table}`")
                rows = cursor.fetchall()
                
                if rows:
                    # Get column names
                    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                    columns = [col[0] for col in cursor.fetchall()]
                    
                    f.write(f"-- Data for table: {table}\n")
                    f.write(f"INSERT INTO `{table}` (`{'`, `'.join(columns)}`) VALUES\n")
                    
                    for j, row in enumerate(rows):
                        # Escape and format values
                        values = []
                        for val in row:
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            else:
                                # Escape single quotes
                                escaped = str(val).replace("'", "''")
                                values.append(f"'{escaped}'")
                        
                        value_str = f"({', '.join(values)})"
                        if j < len(rows) - 1:
                            f.write(f"{value_str},\n")
                        else:
                            f.write(f"{value_str};\n")
                    
                    f.write(f"-- {len(rows)} rows inserted\n\n")
                else:
                    f.write(f"-- No data in table: {table}\n\n")
            
            f.write("SET FOREIGN_KEY_CHECKS=1;\n")
        
        cursor.close()
        conn.close()
        
        # Get file size
        file_size = os.path.getsize(backup_file)
        size_kb = file_size / 1024
        
        print(f"\n✅ Backup completed successfully!")
        print(f"📁 File: {backup_file}")
        print(f"📏 Size: {size_kb:.2f} KB")
        print(f"\nTo restore this backup, run:")
        print(f"  python restore_database.py {os.path.basename(backup_file)}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating backup: {e}")
        return False

if __name__ == '__main__':
    success = backup_database()
    if not success:
        print("\nBackup failed. Please check your MySQL connection and try again.")
