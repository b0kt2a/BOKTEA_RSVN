import sqlite3

def is_duplicate_name(name):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stores WHERE name = ?", (name,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# 직접 테스트
if __name__ == "__main__":
    name_to_check = input("중복 확인할 매장명을 입력하세요: ")
    if is_duplicate_name(name_to_check):
        print("이미 존재하는 매장입니다!")
    else:
        print("새로 추가 가능합니다.")
