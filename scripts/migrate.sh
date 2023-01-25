#!/bin/sh

SQL_DIR="./sql"

migrations=('V001__onchan_init.sql')
for migration in "${migrations[@]}"; do
	sqlite3 onchan.db < "$SQL_DIR/$migration"
done
