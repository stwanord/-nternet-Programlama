import pyodbc

def get_db_connection():
    # \seten kısmını sildik çünkü Configuration Manager'da sadece MSSQLSERVER görünüyor
    server = 'LAPTOP-R4VQ2E4F' 
    database = 'Kütüphane_Sistemi'
    
    conn_str = (
        "Driver={SQL Server};"
        f"Server={server};"
        f"Database={database};"
        "Trusted_Connection=yes;"
    )
    
    try:
        return pyodbc.connect(conn_str)
    except Exception as e:
        print(f"Bağlantı hatası: {e}")
        raise e