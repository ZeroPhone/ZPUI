# coding=utf-8
import argparse
import doctest

import os

from address_book import AddressBook, ZPUI_HOME, Contact
from apps import ZeroApp
from zpui_lib.helpers import setup_logger
from ui import NumberedMenu, Listbox
from vcard_converter import VCardContactConverter

logger = setup_logger(__name__, "info")


class ContactApp(ZeroApp):

    menu_name = "Contacts"

    def can_load(self):
        # needs to be updated for and tested on platforms that are not ZP.
        # also, it might've broken with changes to `flatten` in zpui_lib
        return False, "app mothballed until it's ready to be used"

    def init_app(self):
        self.address_book = AddressBook()

    def on_start(self):
        self.address_book.load_from_file()
        self.menu = NumberedMenu(self.create_menu_content(), self.i, self.o, prepend_numbers=False)
        self.menu.activate()

    def create_menu_content(self):
        all_contacts = self.address_book.contacts
        return [[c.short_name(), lambda x=c: self.create_contact_page(x)] for c in all_contacts]

    def create_contact_page(self, contact):
        # type: (Contact) -> None
        contact_attrs = [getattr(contact, a) for a in contact.get_filled_attributes()]
        Listbox(i=self.i, o=self.o, contents=contact_attrs).activate()


def find_contact_files(folder):
    # type: (str) -> list(str)
    home = os.path.expanduser(folder)
    if not os.path.exists(home):
        os.mkdir(home)
    contact_card_files = [os.path.join(home, f) for f in os.listdir(home) if f.lower().endswith("vcf")]
    return contact_card_files


def load_vcf(folder):
    # type: (str) -> None
    contact_card_files = find_contact_files(folder)
    contacts = VCardContactConverter.from_vcards(contact_card_files)

    address_book = AddressBook()
    for contact in contacts:
        address_book.add_contact(contact)
    address_book.save_to_file()
    logger.info("Saved to {}".format(address_book.get_save_file_path()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--src-folder', dest='src_folder', action='store', metavar="DIR",
                        help='Folder to read vcard from', default=ZPUI_HOME)
    parser.add_argument('-t', '--run-tests', dest='test', action='store_true', default=False)
    arguments = parser.parse_args()

    if arguments.test:
        logger.info("Running tests...")
        doctest.testmod()

    load_vcf(arguments.src_folder)
