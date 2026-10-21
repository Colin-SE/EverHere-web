-- 使用管理员连接 MySQL 执行；请将示例密码替换为自己的开发密码。
CREATE DATABASE IF NOT EXISTS life_album CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'life_album'@'localhost' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON life_album.* TO 'life_album'@'localhost';
-- 表结构由 flask db upgrade 创建，避免手工 SQL 与 ORM 模型漂移。
