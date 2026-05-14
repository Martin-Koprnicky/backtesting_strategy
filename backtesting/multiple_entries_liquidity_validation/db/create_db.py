import sqlite3
from pathlib import Path

def read_schema_sql(keep_open = False):
    """Simple script for reading sql schema file."""
    # Create paths
    backtest_path = Path(__file__).parent / 'backtest.db'
    sql_file_path = Path(__file__).parent / 'schema.sql'

    # Create connection between SQL and Python
    connection = sqlite3.connect(backtest_path)
    cursor = connection.cursor()

    # Open sql file and read content of it
    with open(sql_file_path, 'r') as sql_file:
        sql_content = sql_file.read()

    # Execute sql content and close connection
    cursor.executescript(sql_content)
    connection.commit()

    if keep_open:
        return connection
    else:
        connection.close()
        return None

