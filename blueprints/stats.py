import datetime
import sqlite3
import os
from flask import (
    Blueprint, render_template, g, abort
)
from flask_babel import gettext as _
from contextlib import closing
import database
from anx_library import get_anx_user_dirs

bp = Blueprint('stats', __name__, url_prefix='/stats')

def format_reading_time(seconds):
    if not seconds or seconds == 0:
        return _("0 minutes")
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return _("%(hours)s hours %(minutes)s minutes", hours=int(hours), minutes=int(minutes))
    return _("%(minutes)s minutes", minutes=int(minutes))

@bp.route('/<username>')
def user_stats(username):
    db = database.get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    if user is None:
        abort(404)

    is_owner = g.user and g.user.id == user['id']

    if not user['stats_enabled']:
        return _("This user has disabled their stats page."), 403

    if not user['stats_public'] and not is_owner:
        return _("This user's stats page is private."), 403

    dirs = get_anx_user_dirs(user['username'])
    if not dirs or not os.path.exists(dirs["db_path"]):
        return _("Anx library not found for this user."), 404

    with closing(sqlite3.connect(dirs["db_path"])) as user_db:
        user_db.row_factory = sqlite3.Row
        cursor = user_db.cursor()

        # --- 摘要统计 ---
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

        # --- 热力图数据 ---
        one_year_ago = today - datetime.timedelta(days=365)
        cursor.execute(
            """
            SELECT date, SUM(reading_time) as total_time
            FROM tb_reading_time
            WHERE date >= ?
            GROUP BY date
            """,
            (one_year_ago.strftime('%Y-%m-%d'),)
        )
        reading_times = cursor.fetchall()

        # 将阅读时间转换为 Cal-Heatmap 所需的格式
        heatmap_data = [{"date": row['date'], "value": row['total_time'], "title": f"{row['date']}: {format_reading_time(row['total_time'])}"} for row in reading_times]

        # 获取书籍进度和总阅读时间
        cursor.execute(
            """
            SELECT 
                b.id,
                b.title, 
                b.author, 
                b.reading_percentage,
                b.update_time,
                b.cover_path,
                b.rating,
                b.description,
                SUM(rt.reading_time) as total_reading_time
            FROM tb_books b
            LEFT JOIN tb_reading_time rt ON b.id = rt.book_id
            WHERE b.is_deleted = 0
            GROUP BY b.id
            ORDER BY b.update_time DESC
            """
        )
        books = [dict(row) for row in cursor.fetchall()]

    for book in books:
        book['formatted_reading_time'] = format_reading_time(book['total_reading_time'])

    reading_books = [book for book in books if book['reading_percentage'] < 1]
    finished_books = [book for book in books if book['reading_percentage'] >= 1]

    # Calculate the precise start date for the heatmap (11 months ago, 1st day)
    today = datetime.datetime.utcnow().date()
    target_month = today.month - 11
    target_year = today.year
    if target_month <= 0:
        target_month += 12
        target_year -= 1
    heatmap_start_date = datetime.date(target_year, target_month, 1)

    return render_template('stats.html',
                           user=user,
                           summary_stats=summary_stats,
                           heatmap_data=heatmap_data,
                           heatmap_start_date=heatmap_start_date.strftime('%Y-%m-%d'),
                           reading_books=reading_books,
                           finished_books=finished_books,
                           no_nav=True)