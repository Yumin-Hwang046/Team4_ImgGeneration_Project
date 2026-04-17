"""
DB 초기화 스크립트 (테스트용)
실행: python reset.py
"""
from sqlalchemy import text
from db import engine


def run():
    with engine.connect() as conn:
        conn.execute(text('SET FOREIGN_KEY_CHECKS=0'))
        conn.execute(text('DELETE FROM upload_schedules'))
        conn.execute(text('DELETE FROM generated_images'))
        conn.execute(text('DELETE FROM generations'))
        conn.execute(text('DELETE FROM calendar_events'))
        conn.execute(text('DELETE FROM users'))
        conn.execute(text('SET FOREIGN_KEY_CHECKS=1'))
        conn.commit()
        print('DB 초기화 완료')


if __name__ == '__main__':
    run()
