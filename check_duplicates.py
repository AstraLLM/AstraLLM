#!/usr/bin/env python3
"""Check for duplicate trades in database"""

import sqlite3

db_path = "data/bot_state.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Total trades
cursor.execute('SELECT COUNT(*) FROM trades')
total = cursor.fetchone()[0]
print(f'Total trades in DB: {total}')

# Unique aster_trade_id
cursor.execute('SELECT COUNT(DISTINCT aster_trade_id) FROM trades WHERE aster_trade_id IS NOT NULL')
unique = cursor.fetchone()[0]
print(f'Unique aster_trade_id: {unique}')

# Find duplicates
cursor.execute('''
    SELECT aster_trade_id, COUNT(*) as count
    FROM trades
    WHERE aster_trade_id IS NOT NULL
    GROUP BY aster_trade_id
    HAVING count > 1
''')
dups = cursor.fetchall()
print(f'\nDuplicates found: {len(dups)}')

if dups:
    print('\nFirst 10 duplicates:')
    for dup in dups[:10]:
        print(f'  aster_trade_id={dup[0]}: {dup[1]} copies')

# Show example
cursor.execute('''
    SELECT id, aster_trade_id, symbol, strategy, pnl, created_at
    FROM trades
    LIMIT 10
''')
print('\n\nSample trades:')
for row in cursor.fetchall():
    print(f'  ID={row[0]}, aster_id={row[1]}, {row[2]}, {row[3]}, pnl={row[4]}, created={row[5]}')

conn.close()
