# coding=utf-8
import argparse
import doctest

import os

from address_book import AddressBook, ZPUI_HOME
from contact import Contact
from apps import ZeroApp
from helpers import setup_logger
from ui import (NumberedMenu, Listbox, Menu, LoadingIndicator, DialogBox,
                PrettyPrinter as Printer,  UniversalInput)
from distutils.spawn import find_executable
from helpers.vdirsyncer import (vdirsyncer_sync, vdirsyncer_discover,
                                vdirsyncer_set_carddav_remote,
                                vdirsyncer_get_storage_directory_for,
                                vdirsyncer_generate_config)

logger = setup_logger(__name__, 'info')

class ContactApp(ZeroApp):
    def __init__(self, i, o):
        super(ContactApp, self).__init__(i, o)
        self.menu_name = 'Contacts'
        self.address_book = AddressBook()
        self.menu = None
        self.vdirsyncer_executable = find_executable('vdirsyncer')

    def on_start(self):
        self.reload()

    def reload(self):
        self.address_book.load_from_file()
        self.menu = NumberedMenu(self.build_main_menu_content(), self.i,
                                 self.o, prepend_numbers=False)
        self.menu.activate()

    def build_main_menu_content(self):
        all_contacts = self.address_book.contacts
        menu_entries = [['|| Actions', lambda: self.open_actions_menu()]]
        for c in all_contacts:
            menu_entries.append([c.short_name(), lambda x=c:
                                 self.open_contact_details_page(x)])

        return menu_entries

    def open_contact_details_page(self, contact):
        # type: (Contact) -> None
        contact_attrs = [getattr(contact, a) for a in
                         contact.get_filled_attributes()]
        Listbox(contact_attrs, self.i, self.o).activate()

    def open_actions_menu(self):
        menu_contents = [
            ['CardDAV Setup Wizard', lambda: self.open_remote_setup_wizard()],
            ['CardDAV Sync', lambda: self.synchronize_carddav()],
            ['Reset address book', lambda: self.reset_addressbook()]
        ]
        Menu(menu_contents, self.i, self.o, name='My menu').activate()

    def reset_addressbook(self):
        alert = 'This action will delete all of your contacts. Are you sure?'
        do_reset = DialogBox('yc', self.i, self.o, message=alert,
                             name='Address book reset').activate()

        if do_reset:
            self.address_book.reset()
            announce = 'All of your contacts were deleted.'
            Printer(announce, self.i, self.o, sleep_time=2, skippable=True)
            # Reload the now empty address book
            self.reload()

    def synchronize_carddav(self):
        if (not os.path.isfile(self.vdirsyncer_executable) or
        not os.access(self.vdirsyncer_executable, os.X_OK)):
            Printer('Could not execute vdirsyncer.', self.i, self.o,
                    sleep_time=2, skippable=True)
            return;

        with LoadingIndicator(self.i, self.o, message='Syncing contacts'):
            exit_status = vdirsyncer_sync('contacts')

        if (exit_status != 0):
            error_msg = "Error in contact synchronization. See ZPUI logs for \
            details."
            Printer(error_msg, self.i, self.o, sleep_time=3)
            self.open_actions_menu()

        with LoadingIndicator(self.i, self.o, message='Importing contacts'):
            self.address_book.import_vcards_from_directory(
                vdirsyncer_get_storage_directory_for('contacts')
            )
            self.address_book.save_to_file()

        # Reload the synced address book
        self.reload()

    def open_remote_setup_wizard(self):
        # Define wizard fields
        url_field = UniversalInput(self.i, self.o,
                                   message='CardDAV URL:',
                                   name='CardDAV URL field')
        username_field = UniversalInput(self.i, self.o,
                                        message='CardDAV Username:',
                                        name='CardDAV username field')
        password_field = UniversalInput(self.i, self.o,
                                        message='CardDAV Password:',
                                        name='CardDAV password field')

        # Run wizard
        url = url_field.activate()
        username = username_field.activate()
        password = password_field.activate()

        # Update ZPUI vdirsyncer config, generate vdirsyncer config file
        vdirsyncer_set_carddav_remote(url, username, password)
        vdirsyncer_generate_config()

        # Initialize vdirsyncer remote
        with LoadingIndicator(self.i, self.o, message='Initializing remote'):
            exit_status = vdirsyncer_discover('contacts')

        if (exit_status != 0):
            error_msg = "Error in remote initialization. Check vdirsyncer \
            configuration"
            Printer(error_msg, self.i, self.o, sleep_time=3)
            return

        # Synchronize contacts if the user request it
        sync_now = DialogBox('yn', self.i, self.o,
                             message='Remote saved. Sync now?',
                             name='Sync synced contacts').activate()
        if sync_now: self.synchronize_carddav()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    logger.info('Generating vdirsyncer configuration')
    parser.add_argument('-i', '--src-folder', dest='src_folder', action='store', metavar='DIR',
                        help='Folder to read vcard from', default=ZPUI_HOME)
    parser.add_argument('-t', '--run-tests', dest='test', action='store_true', default=False)
    arguments = parser.parse_args()

    if arguments.test:
        logger.info('Running tests...')
        doctest.testmod()

    address_book = AddressBook()
    address_book.import_vcards_from_directory(arguments.src_folder)
    address_book.save_to_file()
