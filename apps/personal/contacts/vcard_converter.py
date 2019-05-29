import vobject

from address_book import Contact
from helpers import setup_logger

logger = setup_logger(__name__, "info")


class VCardContactConverter(object):
    vcard_mapping = {
        'fn': 'name',
        'n': 'name',
        'adr': 'address',
        'tel': 'telephone',
        'email': 'email',
        'url': 'url',
        'note': 'note',
        'org': 'org',
        'title': 'title'
    }

    @staticmethod
    def to_zpui_contact(v_contact):
        # type: (vobject.base.Component) -> Contact
        contact = Contact()
        for key in v_contact.contents.keys():
            if key not in VCardContactConverter.vcard_mapping: continue
            attr = getattr(contact, VCardContactConverter.vcard_mapping[key])
            assert type(attr) == list
            attr += [v.value for v in v_contact.contents[key]]
        return contact

    @staticmethod
    def parse_vcard_file(file_path):
        # type: (str) -> list
        file_content = VCardContactConverter.read_file_content(file_path)
        contacts = [c for c in vobject.readComponents(file_content, ignoreUnreadable=True)]
        logger.info("Found {} contact in file {}", len(contacts), file_path)
        return contacts

    @staticmethod
    def read_file_content(file_path):
        with open(file_path, 'r') as f:
            file_content = f.read()
            return file_content

    @staticmethod
    def from_vcards(contact_card_files):
        # type: (list) -> list
        contacts = []
        for file_path in contact_card_files:
            contacts += VCardContactConverter.parse_vcard_file(file_path)
        logger.info("finished : {} contacts loaded", len(contacts))
        return [VCardContactConverter.to_zpui_contact(c) for c in contacts]

    @classmethod
    def from_string(cls, vcard_string):
        # type: (str) -> list
        # Returns a list of ZPUI contacts from a string in vcard format
        return [c for c in vobject.readComponents(vcard_string, ignoreUnreadable=True)]
