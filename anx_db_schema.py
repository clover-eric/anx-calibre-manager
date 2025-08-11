# -*- coding: utf-8 -*-

ANX_DB_SCHEMA = """
CREATE TABLE android_metadata (
  locale TEXT
);

CREATE TABLE sqlite_sequence (
  name,
  seq
);

CREATE TABLE tb_books (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT,
  cover_path TEXT,
  file_path TEXT,
  last_read_position TEXT,
  reading_percentage REAL,
  author TEXT,
  is_deleted INTEGER,
  description TEXT,
  create_time TEXT,
  update_time TEXT,
  rating REAL,
  group_id INTEGER,
  file_md5 TEXT
);

CREATE TABLE tb_groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT,
  parent_id INTEGER,
  is_deleted INTEGER DEFAULT 0,
  create_time TEXT,
  update_time TEXT,
  FOREIGN KEY (parent_id) REFERENCES tb_groups(id)
);

CREATE TABLE tb_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book_id INTEGER,
  content TEXT,
  cfi TEXT,
  chapter TEXT,
  type TEXT,
  color TEXT,
  create_time TEXT,
  update_time TEXT,
  reader_note TEXT
);

CREATE TABLE tb_reading_time (
  id INTEGER PRIMARY KEY,
  book_id INTEGER,
  date TEXT,
  reading_time INTEGER
);

CREATE TABLE tb_styles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  font_size REAL,
  font_family TEXT,
  line_height REAL,
  letter_spacing REAL,
  word_spacing REAL,
  paragraph_spacing REAL,
  side_margin REAL,
  top_margin REAL,
  bottom_margin REAL
);

CREATE TABLE tb_themes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  background_color TEXT,
  text_color TEXT,
  background_image_path TEXT
);
"""