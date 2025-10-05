import datetime
import sqlite3
import os
from contextlib import closing
from anx_library import get_anx_user_dirs

def format_reading_time(seconds):
    """将秒格式化为易读的字符串。"""
    if not seconds or seconds == 0:
        return "0 minutes"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{int(hours)} hours {int(minutes)} minutes"
    return f"{int(minutes)} minutes"

def get_user_reading_stats(username, time_range):
    """
    获取用户的阅读统计信息。

    Args:
        username (str): 要查询的用户名。
        time_range (str): 时间范围。此参数为必需项。可以是：
            - "all": 获取所有时间的统计数据。
            - "today", "this_week", "this_month", "this_year": 预设的时间范围。
            - "7", "30", "365": 最近 N 天。
            - "YYYY-MM-DD:YYYY-MM-DD": 自定义日期范围。

    Returns:
        dict: 包含统计数据的字典，或在出错时返回 {"error": "..."}。
    """
    dirs = get_anx_user_dirs(username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return {"error": "Anx library not found for this user."}

    with closing(sqlite3.connect(dirs["db_path"])) as user_db:
        user_db.row_factory = sqlite3.Row
        cursor = user_db.cursor()

        # 1. --- 摘要统计 (始终计算) ---
        today = datetime.datetime.utcnow().date()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)

        cursor.execute(
            """
            SELECT
                SUM(CASE WHEN date = ? THEN reading_time ELSE 0 END) as today,
                SUM(CASE WHEN date >= ? THEN reading_time ELSE 0 END) as this_week,
                SUM(CASE WHEN date >= ? THEN reading_time ELSE 0 END) as this_month,
                SUM(CASE WHEN date >= ? THEN reading_time ELSE 0 END) as this_year,
                SUM(reading_time) as total
            FROM tb_reading_time
            """,
            (
                today.strftime('%Y-%m-%d'),
                start_of_week.strftime('%Y-%m-%d'),
                start_of_month.strftime('%Y-%m-%d'),
                start_of_year.strftime('%Y-%m-%d'),
            )
        )
        summary_data = cursor.fetchone()
        summary_stats = {
            'today': format_reading_time(summary_data['today']),
            'this_week': format_reading_time(summary_data['this_week']),
            'this_month': format_reading_time(summary_data['this_month']),
            'this_year': format_reading_time(summary_data['this_year']),
            'total': format_reading_time(summary_data['total'])
        }

        # 2. --- 根据 time_range 计算日期范围 ---
        start_date = None
        end_date = today
        query_all = (time_range == 'all')

        if not query_all:
            if time_range.isdigit():
                start_date = today - datetime.timedelta(days=int(time_range))
            elif ':' in time_range:
                try:
                    start_str, end_str = time_range.split(':')
                    start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
                    end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
                except ValueError:
                    return {"error": "Invalid date range format. Use YYYY-MM-DD:YYYY-MM-DD."}
            else:
                if time_range == "today":
                    start_date = today
                elif time_range == "this_week":
                    start_date = start_of_week
                elif time_range == "this_month":
                    start_date = start_of_month
                elif time_range == "this_year":
                    start_date = start_of_year
        
        # 3. --- 每日阅读时长 ---
        daily_query = "SELECT date, SUM(reading_time) as total_time FROM tb_reading_time"
        daily_params = []
        
        if not query_all and start_date:
            daily_query += " WHERE date >= ? AND date <= ?"
            daily_params.extend([start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')])
        
        daily_query += " GROUP BY date ORDER BY date"
        cursor.execute(daily_query, daily_params)
        daily_data = cursor.fetchall()
        daily_reading_time = [{"date": row['date'], "time": format_reading_time(row['total_time'])} for row in daily_data]

        # 4. --- 书籍统计 ---
        books_query = """
            SELECT
                b.id, b.title, b.author, b.reading_percentage, b.cover_path,
                SUM(rt.reading_time) as total_reading_time
            FROM tb_books b
            LEFT JOIN tb_reading_time rt ON b.id = rt.book_id
        """
        params = []
        
        where_clauses = ["b.is_deleted = 0"]
        if not query_all and start_date:
            where_clauses.append("rt.date >= ? AND rt.date <= ?")
            params.extend([start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')])

        books_query += " WHERE " + " AND ".join(where_clauses)
        books_query += " GROUP BY b.id HAVING total_reading_time > 0 ORDER BY total_reading_time DESC"
        
        cursor.execute(books_query, params)
        books_data = cursor.fetchall()
        books_stats = [
            {
                "id": row['id'],
                "title": row['title'],
                "author": row['author'],
                "reading_percentage": row['reading_percentage'],
                "total_reading_time": format_reading_time(row['total_reading_time']),
                "cover_path": row['cover_path']
            }
            for row in books_data
        ]

        return {
            "summary_stats": summary_stats,
            "daily_reading_time": daily_reading_time,
            "books_stats": books_stats
        }
