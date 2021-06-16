import matplotlib
matplotlib.use('Agg') # prevent backend render and save png error
import matplotlib.pyplot as plt
import config
import requests
import time
import os
import telebot
from telebot import types


bot = telebot.TeleBot(config.token)

def available_currencies():
    """Show list of available currencies."""
    url = requests.get(config.supported_currencies).json()
    currencies = url['symbols']
    currencies_list = ""

    for k, v in currencies.items():
        currencies_list += str(k) + " : " + str(v['description']) + "\n"
    
    return currencies_list

def currency_rates():
    """Display latest currency rates."""
    url = requests.get(config.latest_rates).json()
    currencies = url['rates']
    currencies_list = ""

    for k, v in currencies.items():
        if str(v) == '0':
            continue
        else:
            currencies_list += str(k) + " : " + str(v) + "\n"
    
    return currencies_list

def convert_currency(_from, _to, _amount):
    """Convert defined currency.
    Args:
        _from - currency that we want convert from,
        _to - currency, that we want conert to,
        __amount - amount of currency.
    """
    url = requests.get(f'https://api.exchangerate.host/convert?from={_from}&to={_to}&amount={_amount}&places=2').json()
    curencies = url['result']

    return curencies

def show_histogram(currency, start_date, end_date):
    """
    Make image with historical rates. start_date must be not weekend.
    Args:
        currency = short currency name
        start_date - date from (yyyy-mm-dd)
        end_date - date until (yyyy-mm-dd)
    """
    url = requests.get(f'https://api.exchangerate.host/timeseries?base=USD&symbols={currency}&start_date={start_date}&end_date={end_date}&places=2').json()

    index = url['rates'].keys()
    data = []
    for k in url['rates'].values():
        data.append(k[f'{currency}'])

    plt.rcParams['figure.figsize'] = (18, 10)
    plt.plot(index, data, label='rates')
    plt.gcf().autofmt_xdate()
    plt.legend(loc=1)

    try:
        plt.savefig('rates.png')
    except Exception as e:
        raise e
    plt.clf()

    return None

def rates_date(date):
    url = requests.get(f'https://api.exchangerate.host/{date}?base=USD&places=2').json()
    rates = url['rates']
    _date = url['date']
    rates_list = ""

    for k, v in rates.items():
        if str(v) == '0':
            continue
        else:
            rates_list += str(k) + " : " + str(v) + "\n"

    return rates_list


@bot.message_handler(commands=['start', 'help'])
def greet(message):
    bot.send_message(message.chat.id, config.help_start)

@bot.message_handler(commands=['qc', 'quick'])
def quick_command(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton('/currency')
    btn2 = types.KeyboardButton('/rates')
    btn3 = types.KeyboardButton('/exchange')
    btn4 = types.KeyboardButton('/histogram')
    btn5 = types.KeyboardButton('/date')
    markup.add(btn1, btn2, btn3, btn4, btn5)
    bot.send_message(message.chat.id, "Choose command:", reply_markup=markup)

@bot.message_handler(commands=['currencies', 'currency'])
def currencies(message):
    try:
        bot.send_message(message.chat.id, available_currencies())
    except Exception:
        # if message length more than 4096 symbols, split it
        for x in range(0, len(available_currencies()), 4096):
            bot.send_message(message.chat.id, available_currencies()[x:x+4096])

@bot.message_handler(commands=['rates', 'list'])
def currencies_rate(message):
    bot.send_message(message.chat.id, currency_rates())

# currency convertion chain
@bot.message_handler(commands=['xe', 'exchange', 'convert'])
def currency_converter(message):
    bot.send_message(message.chat.id,
        "What currency do you want to convert?", currency_command(message))
    bot.register_next_step_handler(message, currency_converter2)

def currency_command(message):
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True,
        selective=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton('UAH')
    btn2 = types.KeyboardButton('USD')
    btn3 = types.KeyboardButton('EUR')
    btn4 = types.KeyboardButton('TRY')
    btn5 = types.KeyboardButton('JPY')
    btn6 = types.KeyboardButton('GBP')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    bot.send_message(message.chat.id, "Choose currency or type yours:",
        reply_markup=markup)

def currency_converter2(message):
    global _convert_from
    _convert_from = message.text
    bot.send_message(message.chat.id,
                            "To which currency?", currency_command(message))
    bot.register_next_step_handler(message, currency_converter3)

def currency_converter3(message):
    global _convert_to
    _convert_to = message.text
    bot.send_message(message.chat.id, "Please, type amount.")
    bot.register_next_step_handler(message, currency_converter_final)

def currency_converter_final(message):
    _amount = message.text
    try:
        bot.send_message(message.chat.id, convert_currency(
                                    _convert_from, _convert_to, _amount))
    except Exception:
        bot.send_message(message.chat.id, "Something went wrong :(")
    quick_command(message)

# historical time-series chain
@bot.message_handler(commands=['histogram', 'graph'])
def histogram_step1(message):
    bot.send_message(message.chat.id, available_currencies())
    bot.send_message(message.chat.id,
        "Type currency abbreviation from previous list.",
        currency_command(message))
    bot.register_next_step_handler(message, history_step2)

def history_step2(message):
    global _historical_currency
    _historical_currency = message.text
    bot.send_message(message.chat.id,
        "Type start date in format 'yyyy-mm-dd,' e.g.(2021-05-28). Must be not weekend.")
    bot.register_next_step_handler(message, history_step3)

def history_step3(message):
    global _historical_start_date
    _historical_start_date = message.text
    bot.send_message(message.chat.id,
                "Type end date in format 'yyyy-mm-dd', e.g.(2021-06-04)")
    bot.register_next_step_handler(message, show_history_rates)

def show_history_rates(message):
    _historical_end_date = message.text
    try:
        show_histogram(
            _historical_currency, _historical_start_date, _historical_end_date)
        bot.send_message(message.chat.id, "Here it comes!")
        time.sleep(2)
        bot.send_photo(message.chat.id, (open('rates.png', 'rb')))
        time.sleep(1)
        os.remove('rates.png')
    except Exception as e:
        bot.send_message(message.chat.id, 
            "No exchange rate data is available for the selected currency.")
        print(e)
    quick_command(message)

# historical date rates
@bot.message_handler(commands=['hr', 'date'])
def date_rates(message):
    bot.send_message(message.chat.id, "Type date to check rates")
    bot.register_next_step_handler(message, date_rates_final)

def date_rates_final(message):
    date_for_rates = message
    bot.send_message(message.chat.id, rates_date(date_for_rates))

bot.polling()
