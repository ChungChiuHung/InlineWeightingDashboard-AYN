import sqlite3
import os

# 設定資料庫路徑
DB_PATH = "data/history.db"

def check_database():
    print(f"--- 檢查資料庫: {DB_PATH} ---")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 錯誤: 找不到資料庫檔案！請確認路徑或是否已啟動過主程式。")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. 檢查所有表格
        print("\n[1. 資料表列表]")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("⚠️  警告: 資料庫是空的，沒有任何表格。")
        else:
            for t in tables:
                print(f"  - {t[0]}")

        # 2. 檢查 fish_type 表格內容
        if ('fish_type',) in tables:
            print("\n[2. 魚種設定 (fish_type) 內容]")
            cursor.execute("SELECT * FROM fish_type")
            rows = cursor.fetchall()
            if not rows:
                print("⚠️  警告: fish_type 表格存在，但裡面是空的 (No Data)。")
            else:
                print(f"  {'代碼 (Code)':<10} | {'名稱 (Name)'}")
                print("  " + "-"*30)
                for row in rows:
                    # row[0] 是 code, row[1] 是 name
                    print(f"  {row[0]:<10} | {row[1]}")
        else:
            print("\n❌ 錯誤: 找不到 `fish_type` 表格！(init_db 可能未成功執行)")

        # 3. 檢查 history 表格 (顯示最新 5 筆)
        if ('history',) in tables:
            print("\n[3. 歷史記錄 (history) 最新 5 筆]")
            cursor.execute("SELECT * FROM history ORDER BY id DESC LIMIT 5")
            rows = cursor.fetchall()
            if not rows:
                print("  (尚無歷史數據)")
            else:
                for row in rows:
                    print(f"  {row}")

        conn.close()
        print("\n--- 檢查完成 ---")

    except Exception as e:
        print(f"\n❌ 發生例外錯誤: {e}")

if __name__ == "__main__":
    check_database()