#!/bin/sh
#
# Crea il database di appoggio di Metabase alla prima inizializzazione.
#
# Metabase tiene cruscotti, domande e utenti in un database suo. Con
# `MB_DB_TYPE=postgres` si aspetta di trovarlo già creato: se non c'è, non
# parte, e il messaggio parla di «connection checkout timed out» — che non
# dice a nessuno qual è il problema vero.
#
# PostgreSQL esegue questa cartella **solo quando il volume è vuoto**, cioè
# la prima volta. È il posto giusto: la creazione avviene prima che Metabase
# provi a collegarsi, senza un passaggio manuale da ricordare.
#
# La prova su macchina pulita (M8-T2) esiste per trovare cose come questa: il
# database era stato creato a mano durante lo sviluppo, e il comando non era
# scritto da nessuna parte.

set -e

DATABASE="${METABASE_DB_NAME:-metabase}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    SELECT 'CREATE DATABASE "$DATABASE"'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DATABASE')\gexec
SQL

echo "database di appoggio di Metabase pronto: $DATABASE"
