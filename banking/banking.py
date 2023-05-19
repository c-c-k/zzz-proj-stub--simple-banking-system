from pathlib import Path
from random import randint
import sqlite3

import messages

BIN_PREFIX = "400000"
SCHEMA = """
CREATE TABLE IF NOT EXISTS card (
    id INTEGER PRIMARY KEY,
    number TEXT UNIQUE NOT NULL,
    pin TEXT NOT NULL,
    balance INTEGER DEFAULT 0
);
"""

_db = None
next_raw_card_num = None
g = {}


class Card:
    def __init__(self, id_, card_num, card_pin, balance_):
        self.id = id_
        self.card_num = card_num
        self.card_pin = card_pin
        self.balance = balance_


def get_db():
    global _db
    if _db is None:
        _db = sqlite3.connect('card.s3db')
    return _db


def init_db():
    if Path('card.s3db').exists():
        return
    db = get_db()
    # cur = db.cursor()
    db.execute(SCHEMA)
    db.commit()


def init_next_raw_card_num():
    global next_raw_card_num
    db = get_db()
    max_card_num = db.execute(
        "SELECT max(number) from card").fetchone()[0]
    max_account_number = ("0"*9 if max_card_num is None
                          else max_card_num[6: -1])
    next_raw_card_num = int(
        BIN_PREFIX + max_account_number + "0") + 10


def print_message(message):
    print(message.strip())


def menu(message, url):
    print_message(message)
    choice = input().strip()
    controller(url, choice)


def exit_():
    print_message(messages.EXIT)


def menu_main_anonymous():
    menu(messages.MAIN_MENU_ANONYMOUS, "menu/main")


def menu_main_authenticated():
    menu(messages.MAIN_MENU_AUTHENTICATED, "menu/main")


def gen_card_num_checksum(card_number):
    card_number = int(card_number)
    control_number = 0
    for digit_place in range(16):
        digit = card_number % 10
        card_number //= 10
        if digit_place % 2 != 0:
            digit *= 2
            digit -= 9 if digit > 9 else 0
        control_number += digit
    return (10 - control_number % 10) % 10


def gen_card_num():
    global next_raw_card_num
    card_number = (
        next_raw_card_num
        + gen_card_num_checksum(next_raw_card_num))
    next_raw_card_num += 10
    return f"{card_number:0>16}"


def gen_card_pin():
    return f"{randint(0, 9999):0>4}"


def create_account():
    card_num = gen_card_num()
    card_pin = gen_card_pin()
    db = get_db()
    # cur = db.cursor()
    db.execute("""
    INSERT INTO card (number, pin)
    VALUES (?, ?)
    """, (card_num, card_pin))
    db.commit()
    controller("auth/create/success", card_num, card_pin)


def create_account_success(card_num, card_pin):
    print_message(messages.CREATE_CARD_SUCCESS.format(
        card_num=card_num, card_pin=card_pin))
    controller("menu/main")


def auth_login():
    print_message(messages.ENTER_CARD_NUM)
    card_num = input()
    print_message(messages.ENTER_CARD_PIN)
    card_pin = input()
    db = get_db()
    # cur = db.cursor()
    card_info = db.execute("""
    SELECT *
    FROM card
    WHERE number = ? AND pin = ?
    """, (card_num, card_pin)).fetchone()
    controller(
        "auth/is_valid",
        card_info is not None,
        card_info
    )


def login_success(card_info):
    global g
    g['card'] = Card(*card_info)
    print_message(messages.LOGIN_SUCCESS)
    controller("menu/main")


def login_failed():
    print_message(messages.LOGIN_FAILED)
    controller("menu/main")


def auth_logout():
    global g
    g.pop('card')
    print_message(messages.LOGOUT_SUCCESS)
    controller("menu/main")


def balance():
    card = g['card']
    print_message(
        messages.BALANCE.format(balance=card.balance))
    controller("menu/main")


def controller(*command):
    match command:
        case ["menu/main"] if 'card' in g:
            menu_main_authenticated()
        case ["menu/main", "1"] if 'card' in g:
            balance()
        case ["menu/main", "2"] if 'card' in g:
            auth_logout()
        case ["menu/main"]:
            menu_main_anonymous()
        case ["menu/main", "1"]:
            create_account()
        case ["menu/main", "2"]:
            auth_login()
        case ["menu/main", "0"]:
            exit_()
        case ["auth/create/success", card_num, card_pin]:
            create_account_success(card_num, card_pin)
        case ["auth/is_valid", True, card_num]:
            login_success(card_num)
        case ["auth/is_valid", False, _]:
            login_failed()


def main():
    init_db()
    init_next_raw_card_num()
    controller("menu/main")


if __name__ == "__main__":
    main()
