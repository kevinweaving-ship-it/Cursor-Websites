#!/bin/bash
# Install Dolibarr 24.0.2 on the existing Mail-in-a-Box host.
# Does not touch upp.db, QuickBooks, billing cron, or dash files.
set -euo pipefail
VER=24.0.2
APP=/opt/dolibarr
DOC=/home/user-data/dolibarr-documents
WWWCONF=/home/user-data/www/gowifi.co.za.conf
SRC=$(cd "$(dirname "$0")" && pwd)
SECRETS=/root/secrets/dolibarr.env

export DEBIAN_FRONTEND=noninteractive

if ! dpkg -s mariadb-server >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq mariadb-server php8.0-mysql php8.0-cli
fi
if ! php -m | grep -qi mysqli; then
  apt-get install -y -qq php8.0-mysql
  systemctl reload php8.0-fpm
fi

# Small-box MariaDB — do not starve mail/dash.
mkdir -p /etc/mysql/mariadb.conf.d
cat > /etc/mysql/mariadb.conf.d/99-gowifi-dolibarr.cnf <<'CNF'
[mysqld]
innodb_buffer_pool_size = 128M
innodb_log_file_size = 48M
max_connections = 40
performance_schema = OFF
skip-name-resolve
CNF
systemctl enable --now mariadb
systemctl restart mariadb

if [ ! -f "$SECRETS" ]; then
  DBPASS=$(openssl rand -base64 24 | tr -d '/+=' | head -c 28)
  ADMINPASS=$(openssl rand -base64 18 | tr -d '/+=' | head -c 20)
  umask 077
  cat > "$SECRETS" <<ENV
DOLIBARR_VERSION=$VER
DOLIBARR_URL=https://gowifi.co.za/dolibarr/
DOLIBARR_DB_NAME=dolibarr
DOLIBARR_DB_USER=dolibarr
DOLIBARR_DB_PASS=$DBPASS
DOLIBARR_ADMIN=admin
DOLIBARR_ADMIN_PASS=$ADMINPASS
DOLIBARR_DOCUMENTS=$DOC
DOLIBARR_ROOT=$APP/htdocs
ENV
  chmod 600 "$SECRETS"
fi
# shellcheck disable=SC1090
source "$SECRETS"

mysql --protocol=socket -u root <<SQL
CREATE DATABASE IF NOT EXISTS \`${DOLIBARR_DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DOLIBARR_DB_USER}'@'localhost' IDENTIFIED BY '${DOLIBARR_DB_PASS}';
ALTER USER '${DOLIBARR_DB_USER}'@'localhost' IDENTIFIED BY '${DOLIBARR_DB_PASS}';
GRANT ALL PRIVILEGES ON \`${DOLIBARR_DB_NAME}\`.* TO '${DOLIBARR_DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

if [ ! -f "$APP/htdocs/index.php" ]; then
  mkdir -p /opt
  TMP=/tmp/dolibarr-$VER.tgz
  curl -fsSL -o "$TMP" "https://github.com/Dolibarr/dolibarr/archive/refs/tags/${VER}.tar.gz"
  tar -xzf "$TMP" -C /opt
  rm -f "$TMP"
  rm -rf "$APP"
  mv "/opt/dolibarr-${VER}" "$APP"
fi
mkdir -p "$DOC" "$APP/htdocs/conf"
chown -R www-data:www-data "$DOC" "$APP/htdocs/conf"

# Forced install values for the web installer (used if tables are empty).
cat > "$APP/htdocs/install/install.forced.php" <<PHP
<?php
\$force_install_nophpinfo = true;
\$force_install_noedit = 2;
\$force_install_message = 'GoWiFi trial';
\$force_install_main_data_root = '${DOC}';
\$force_install_type = 'mysqli';
\$force_install_dbserver = 'localhost';
\$force_install_port = '3306';
\$force_install_database = '${DOLIBARR_DB_NAME}';
\$force_install_prefix = 'llx_';
\$force_install_createdatabase = false;
\$force_install_databaselogin = '${DOLIBARR_DB_USER}';
\$force_install_databasepass = '${DOLIBARR_DB_PASS}';
\$force_install_createuser = false;
\$force_install_mainforcehttps = true;
PHP
chown www-data:www-data "$APP/htdocs/install/install.forced.php"

if [ ! -f "$APP/htdocs/conf/conf.php" ]; then
  cat > "$APP/htdocs/conf/conf.php" <<PHP
<?php
\$dolibarr_main_url_root='https://gowifi.co.za/dolibarr';
\$dolibarr_main_document_root='${APP}/htdocs';
\$dolibarr_main_url_root_alt='/custom';
\$dolibarr_main_document_root_alt='${APP}/htdocs/custom';
\$dolibarr_main_data_root='${DOC}';
\$dolibarr_main_db_host='localhost';
\$dolibarr_main_db_port='3306';
\$dolibarr_main_db_name='${DOLIBARR_DB_NAME}';
\$dolibarr_main_db_prefix='llx_';
\$dolibarr_main_db_user='${DOLIBARR_DB_USER}';
\$dolibarr_main_db_pass='${DOLIBARR_DB_PASS}';
\$dolibarr_main_db_type='mysqli';
\$dolibarr_main_db_character_set='utf8mb4';
\$dolibarr_main_db_collation='utf8mb4_unicode_ci';
\$dolibarr_main_authentication='dolibarr';
\$dolibarr_main_prod=0;
\$dolibarr_main_force_https=1;
PHP
  chown www-data:www-data "$APP/htdocs/conf/conf.php"
  chmod 660 "$APP/htdocs/conf/conf.php"
fi

# Persist nginx (Mail-in-a-Box regenerates local.conf; this include survives).
if [ -f "$SRC/nginx-dolibarr.conf" ] && [ -f "$WWWCONF" ]; then
  if ! grep -q 'location /dolibarr/' "$WWWCONF"; then
    printf '\n' >> "$WWWCONF"
    cat "$SRC/nginx-dolibarr.conf" >> "$WWWCONF"
  fi
  nginx -t
  systemctl reload nginx
fi

echo "dolibarr-files-ready $VER"
