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


class ValidationError(Exception):
    pass

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


def add_income():
    print_message(messages.ENTER_INCOME)
    new_income = int(input())
    card = g['card']
    card.balance += new_income
    db = get_db()
    db.execute("""
    UPDATE card
    SET balance = ?
    WHERE number = ?
    """, (card.balance, card.card_num))
    db.commit()
    print_message(messages.INCOME_ADDED)
    controller("menu/main")


def close_account():
    card = g['card']
    db = get_db()
    db.execute("""
    DELETE FROM card
    WHERE number = ?
    """, (card.card_num,))
    db.commit()
    g.pop('card')
    print_message(messages.ACOUNT_DELETED)
    controller("menu/main")


def validate_not_same_account(target_card):
    if target_card == g['card'].card_num:
        raise ValidationError(messages.ERROR_SAME_ACCOUNT)


def validate_target_card_checksum(target_card):
    raw_target_card = int(target_card[:-1] + "0")
    if gen_card_num_checksum(raw_target_card) != int(target_card[-1]):
        raise ValidationError(messages.ERROR_WRONG_CHECKSUM)


def validate_target_card_exists(target_card):
    db = get_db()
    target_card_exists = db.execute("""
    SELECT true FROM card WHERE number = ?
    """, (target_card,)).fetchone()
    if not target_card_exists:
        raise ValidationError(messages.ERROR_TRANSFER_ACCOUNT_DOES_NOT_EXIST)


def validate_sufficient_funds(transfer_amount):
    if g['card'].balance < transfer_amount:
        raise ValidationError(messages.ERROR_INSUFFICIENT_FUNDS)


def start_transfer():
    print_message(messages.ENTER_CARD_NUM_FOR_TRANSFER)
    target_card = input()
    try:
        validate_not_same_account(target_card)
        validate_target_card_checksum(target_card)
        validate_target_card_exists(target_card)
    except ValidationError as err:
        print_message(err.args[0])
        controller("menu/main")
        return
    print_message(messages.ENTER_AMOUNT_FOR_TRANSFER)
    transfer_amount = int(input())
    try:
        validate_sufficient_funds(transfer_amount)
    except ValidationError as err:
        print_message(err.args[0])
        controller("menu/main")
        return
    controller("transfer_funds", target_card, transfer_amount)


def execute_transfer(target_card, transfer_amount):
    card = g['card']
    db = get_db()
    db.execute("""
    UPDATE card
    SET balance = balance - ?
    WHERE number = ?
    """, (transfer_amount, card.card_num))
    db.execute("""
    UPDATE card
    SET balance = balance + ?
    WHERE number = ?
    """, (transfer_amount, target_card))
    db.commit()
    card.balance -= transfer_amount
    print_message(messages.SUCCESS)
    controller("menu/main")


def controller(*command):
    match command:
        case ["menu/main"] if 'card' in g:
            menu_main_authenticated()
        case ["menu/main", "1"] if 'card' in g:
            balance()
        case ["menu/main", "2"] if 'card' in g:
            add_income()
        case ["menu/main", "3"] if 'card' in g:
            start_transfer()
        case ["menu/main", "4"] if 'card' in g:
            close_account()
        case ["menu/main", "5"] if 'card' in g:
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
        case ["transfer_funds", target_card, transfer_amount]:
            execute_transfer(target_card, transfer_amount)


def main():
    init_db()
    init_next_raw_card_num()
    controller("menu/main")


if __name__ == "__main__":
    main()
