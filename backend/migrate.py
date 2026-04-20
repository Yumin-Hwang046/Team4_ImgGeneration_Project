"""
DB 마이그레이션 스크립트
실행: python migrate.py
"""
from sqlalchemy import text
from db import engine


MIGRATIONS = [
    # password_hash를 nullable로 변경 (OAuth 유저 지원)
    "ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NULL",

    # Instagram 연동 컬럼 추가
    "ALTER TABLE users ADD COLUMN instagram_user_id VARCHAR(100) NULL UNIQUE",
    "ALTER TABLE users ADD COLUMN instagram_account_id VARCHAR(100) NULL",
    "ALTER TABLE users ADD COLUMN instagram_access_token VARCHAR(500) NULL",
    "ALTER TABLE users ADD COLUMN instagram_username VARCHAR(100) NULL",
]


def run():
    with engine.connect() as conn:
        for sql in MIGRATIONS:
            col = sql.split("COLUMN")[-1].strip().split()[0]
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"  완료: {col}")
            except Exception as e:
                msg = str(e)
                if "Duplicate column name" in msg or "already exists" in msg:
                    print(f"  건너뜀 (이미 존재): {col}")
                else:
                    print(f"  오류: {col} → {msg}")


if __name__ == "__main__":
    print("마이그레이션 시작...")
    run()
    print("완료!")
