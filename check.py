#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
from psycopg2 import sql

# -----------------------------
# 【一】请将下面改成你的真实连接字符串
#    如果在本地运行，请使用“Connect”页面里给出的
#    公网连接（通常形如 containers-xxx.railway.app:5432?...?sslmode=require）
#    如果你在 Railway Console/Terminal 里执行，这里也可以用 trolley.proxy.rlwy.net:55555
#------------------------------
DB_URL = "postgresql://postgres:QQgNtyhQHJCyejpsGgVaoKfNtaXEzBvw@trolley.proxy.rlwy.net:55555/railway"


def find_media_columns(conn):
    """
    查找 public schema 下列名正好是 'media' 的所有表。
    返回类似 [('moments', 'media'), ('travel_notes', 'media'), ...]
    """
    with conn.cursor() as cur:
        query = """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_name = 'media'
            ORDER BY table_name;
        """
        cur.execute(query)
        return cur.fetchall()


def fetch_media_paths_from_json(conn, table, column):
    """
    取出 table.column（假定是 jsonb 类型）里的每个数组元素，再筛选那些以 '/static/images/' 或 '/static/videos/' 开头的子串。
    返回示例列表：['/static/images/1749113654_output.gif', '/static/videos/1749113751_video.mkv', ...]
    """
    with conn.cursor() as cur:
        # 1. 如果 media 列就是 jsonb 类型，可以直接 jsonb_array_elements_text(media)
        # 2. 如果 media 列是 text 存储，但内容本质是 JSON，则需要先转换： jsonb_array_elements_text(media::jsonb)
        #   这里假设 media 列是 JSONB 类型，如果你存的是 TEXT，就把 jsonb_array_elements_text(media) 改成 jsonb_array_elements_text(media::jsonb)
        stmt = sql.SQL("""
            SELECT DISTINCT elem AS media_path
            FROM {tbl},
                 jsonb_array_elements_text({tbl}.{col}::jsonb)
 AS elem
            WHERE elem LIKE %s
               OR elem LIKE %s
        """).format(
            tbl=sql.Identifier(table),
            col=sql.Identifier(column)
        )

        # 两个模式：'/static/images/%' 和 '/static/videos/%'
        cur.execute(stmt, ["/static/images/%", "/static/videos/%"])
        rows = cur.fetchall()

    # rows 是 [(path1,), (path2,), ...]，提取成扁平列表
    return [row[0] for row in rows if row[0] is not None]


def main():
    print("🚀 尝试连接数据库，URL：", DB_URL)
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        print("✅ 数据库连接成功！\n")

        # 第一步：找出所有名为 media 的列
        print("🔍 正在查找字段名为 'media' 的表……")
        media_columns = find_media_columns(conn)
        if not media_columns:
            print("❌ 在 public schema 下找不到任何名为 'media' 的列，请检查表设计。")
            return

        print("找到以下表的 media 列：")
        for tbl, col in media_columns:
            print(f"    • {tbl}.{col}")
        print()

        # 第二步：对每个表的 media 列，拆分 JSON 数组并过滤前缀
        print("🔎 开始从 JSON 数组中筛选 '/static/images/' 或 '/static/videos/' 前缀的路径：\n")

        total_found = 0
        for tbl, col in media_columns:
            paths = fetch_media_paths_from_json(conn, tbl, col)
            if paths:
                print(f"—— 表 `{tbl}` 中 {col} 列匹配到 {len(paths)} 条路径：")
                for idx, p in enumerate(paths, start=1):
                    print(f"    {idx}. {p}")
                print()
                total_found += len(paths)

        if total_found == 0:
            print("⚠️ 虽然找到了 `media` 列，但并没有匹配到任何以 `/static/images/` 或 `/static/videos/` 开头的元素。")
        else:
            print(f"🎉 一共找到 {total_found} 条静态资源路径。")

    except Exception as exc:
        print("❌ 脚本执行出现异常：", exc)
    finally:
        if conn:
            conn.close()
            print("\n🔒 已关闭数据库连接。")


if __name__ == "__main__":
    main()

