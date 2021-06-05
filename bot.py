import matplotlib
matplotlib.use('Agg') # prevent backend render and save png error
import matplotlib.pyplot as plt
import config
import telebot
import requests
import sqlite3
import subprocess
import os
import time
from telebot import types
import pandas as pd


bot = telebot.TeleBot(config.token)

api_fx = config.API_fxmarketapi_com

currency_dict = requests.get(config.currencies).json()
previous_timestamp = "1622885054"
timestamp_10min = 600

def get_timestamp():
    "Return current timestamp"
    timestamp_now = currency_dict['timestamp']
    return timestamp_now

def get_rates():
    """Receive data from API call.
    Var:
        rates_dict - variable only with rates.
        rates - variable with rounded decimals.
    """
    rates_dict = currency_dict['rates']
    # round dict values to 2 decimals
    rates = {k :("%.2f" % v) for k,v in rates_dict.items()}
    return rates

def display_rates():
    """Return string with formated rates from API item. Base currency - EUR.
    Var:
        list_rates = string with rates e.g. "USD: 1.21".
        rates = dict. with rounded decimals from get_rates function.
    """
    list_rates = ""
    rates = get_rates()
    for k, v in rates.items():
        list_rates += str(k) + " : " + str(v) + "\n"
    return list_rates

def send_rates():
    """
    Return list of available currencies from database or fresh rates from API
    """
    global previous_timestamp
    print(previous_timestamp)
    timestamp_now = get_timestamp()
    send_rates = ""

    if timestamp_10min > (int(timestamp_now) - int(previous_timestamp)):
        send_rates = load_from_database()
        print("database")
    else:
        send_rates = display_rates()
        try:
            subprocess.Popen("py init_db.py", shell=True)
        except Exception:
            subprocess.Popen("python3 init_db.py", shell=True)
        time.sleep(2)
        previous_timestamp = timestamp_now
        print(previous_timestamp)
        print('from api')

    return send_rates

def load_from_database():
    """Connect and load all rates from database"""
    list_rates = ""
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    cur.execute("SELECT currency, currency_value FROM rates")
    rows = cur.fetchall()
    for i in range(len(rows)):
        list_rates += rows[i][0] + " : " + rows[i][1] + "\n"
    connection.close()
    return list_rates

def convert_value(_from, _to, _amount):
    """
    Convert user defined currency.
    Using API from fxmarketapi.
    """
    convert_url = f"https://fxmarketapi.com/apiconvert?api_key={api_fx}&from={_from}&to={_to}&amount={_amount}"
    convert_response = requests.get(convert_url).json()
    result = str(round(convert_response['total'], 2))
    return result

def convert_10EURO():
    """Convert 10EUR instead of USD to CAD. Values from database."""
    connection = sqlite3.connect('database.db')
    cur = connection.cursor()
    base_currency = "EUR"
    currency_to = "CAD"
    amount = 10
    cur.execute(f"SELECT currency_value FROM rates WHERE currency='{currency_to}'")
    value_to = cur.fetchall()
    result =  float(value_to[0][0]) * float(amount)
    result_r = "%.2f" % result
    connection.close()
    return result_r

def show_history(currency, start_date, end_date):
    """
    Make image with historical rates. start_date must be not weekend.
    Args:
        currency = short currency name
        start_date - date from (yyyy-mm-dd)
        end_date - date until (yyyy-mm-dd)
    """
    df = pd.read_json(f"https://fxmarketapi.com/apipandas?api_key={api_fx}&currency={currency}&start_date={start_date}&end_date={end_date}")

    plt.plot(df['low'], label='low')
    plt.plot(df['high'], label='high')
    plt.legend(loc=1)
    try:
        plt.savefig('rates.png')
    except RuntimeError:
        pass
    plt.clf()
    return

def show_currency_list():
    """Display currency list from fxmarketapi.com"""
    url = requests.get(f"https://fxmarketapi.com/apicurrencies?api_key={api_fx}").json()
    currencies = url['currencies']
    currencies_string = ''
    for k, v in currencies.items():
        currencies_string += str(k) + " : " + str(v) + "\n"
    return currencies_string

@bot.message_handler(commands=['start', 'help'])
def greet(message):
    bot.send_message(message.chat.id, config.help_start)

@bot.message_handler(commands=['list', 'lst'])
def display_currencies(message):
    bot.send_message(message.chat.id, send_rates())
    bot.send_message(message.chat.id, "Base currency - EUR.")

@bot.message_handler(commands=['exchange'])
def convert_usd_to_cad(message):
    """10 EUR convertion to CAD"""
    bot.send_message(message.chat.id, convert_10EURO())

# currency convertion chain, in addition to 10 EUR convertion
@bot.message_handler(commands=['convert', 'xe'])
def convert_step1(message):
    bot.send_message(message.chat.id,
            "What currency do you want to convert? e.g. -'USD', 'CAD', 'TRY'")
    bot.register_next_step_handler(message, convert_step2)

def convert_step2(message):
    bot.send_message(message.chat.id,
                                "To which currency? e.g. -'USD', 'CAD', 'TRY'")
    global convert_from
    convert_from = message.text
    bot.register_next_step_handler(message, convert_step3)

def convert_step3(message):
    global convert_to
    convert_to = message.text
    bot.send_message(message.chat.id, "Enter amount, please.")
    bot.register_next_step_handler(message, convert_result)

def convert_result(message):
    amount = message.text
    try:
        bot.send_message(message.chat.id, "Voila!\n" + convert_value(
                                            convert_from, convert_to, amount))
    except Exception:
        bot.send_message(message.chat.id,
            "Something went wrong :(. Maybe there is no currency in our base.")

# historical chain
@bot.message_handler(commands=['history', 'past'])
def history_step1(message):
    bot.send_message(message.chat.id, show_currency_list())
    bot.send_message(message.chat.id,
                            "Type currency abbreviation from previous list.")
    bot.register_next_step_handler(message, history_step2)

def history_step2(message):
    global historical_currency
    historical_currency = message.text
    bot.send_message(message.chat.id,
        "Type start date in format 'yyyy-mm-dd,' e.g.(2021-05-28). Must be not weekend.")
    bot.register_next_step_handler(message, history_step3)

def history_step3(message):
    global historical_start_date
    historical_start_date = message.text
    bot.send_message(message.chat.id,
                    "Type end date in format 'yyyy-mm-dd', e.g.(2021-06-04)")
    bot.register_next_step_handler(message, show_history_rates)
    
def show_history_rates(message):
    historical_end_date = message.text
    try:
        show_history(
            historical_currency, historical_start_date, historical_end_date)
        bot.send_message(message.chat.id, "Here it comes!")
        time.sleep(3)
        bot.send_photo(message.chat.id, (open('rates.png', 'rb')))
        time.sleep(2)
        os.remove('rates.png')
    except Exception as e:
        bot.send_message(message.chat.id, 
            "No exchange rate data is available for the selected currency.")

bot.polling()
