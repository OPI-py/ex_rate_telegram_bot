import sqlite3
import config
import requests

currency_dict = requests.get(config.currencies).json()
rates = currency_dict['rates']

currency_list = [k for k in rates.keys()]
value_list = ["%.2f" % v for v in rates.values()]
connection = sqlite3.connect('database.db')

with open('schema.sql') as f:
    connection.executescript(f.read())

cur = connection.cursor()
index_range = len(currency_list)

for i in range(index_range):
    try:
        cur.execute("INSERT INTO rates (currency, currency_value) VALUES (?, ?)",
        (currency_list[i], value_list[i]))
        connection.commit()
    except IndexError:
        index_range -= 1

connection.close()
