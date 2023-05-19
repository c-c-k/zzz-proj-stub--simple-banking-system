from random import randint

import messages

BIN_PREFIX = 4000000000000000

next_account_number = 10
accounts = {}
g = {}


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
        print(card_number, digit, control_number)
        control_number += digit
    return (10 - control_number % 10) % 10


def gen_card_num():
    global next_account_number
    card_number = BIN_PREFIX + next_account_number
    card_number += gen_card_num_checksum(card_number)
    next_account_number += 10
    return card_number


def gen_card_pin():
    return randint(0, 9999)


def create_account():
    global accounts
    card_num = gen_card_num()
    card_pin = gen_card_pin()
    accounts[card_num] = card_pin
    controller("auth/create/success", card_num, card_pin)


def create_account_success(card_num, card_pin):
    print_message(messages.CREATE_CARD_SUCCESS.format(
        card_num=card_num, card_pin=card_pin))
    controller("menu/main")


def auth_login():
    print_message(messages.ENTER_CARD_NUM)
    card_num = int(input())
    print_message(messages.ENTER_CARD_PIN)
    card_pin = int(input())
    controller(
        "auth/is_valid",
        accounts.get(card_num, -1) == card_pin,
        card_num
    )


def login_success(card_num):
    global g
    g['card_num'] = card_num
    print_message(messages.LOGIN_SUCCESS)
    controller("menu/main")


def login_failed():
    print_message(messages.LOGIN_FAILED)
    controller("menu/main")


def auth_logout():
    global g
    g.pop('card_num')
    print_message(messages.LOGOUT_SUCCESS)
    controller("menu/main")


def balance():
    print_message(messages.BALANCE.format(balance=0))


def controller(*command):
    match command:
        case ["menu/main"] if 'card_num' in g:
            menu_main_authenticated()
        case ["menu/main", "1"] if 'card_num' in g:
            balance()
        case ["menu/main", "2"] if 'card_num' in g:
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
    controller("menu/main")


if __name__ == "__main__":
    main()
