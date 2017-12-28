import os
import pickle

from helpers import Singleton, flatten
from helpers import setup_logger
from helpers.general import ZPUI_HOME

logger = setup_logger(__name__, "warning")

class AddressBook(Singleton):
    def __init__(self):
        """
        Adds a single contact
        >>> a = AddressBook()
        >>> c1 = Contact(name="john", org="wikipedia")
        >>> a.add_contact(c1)
        >>> len(a.contacts)
        1

        Adds another contact so similar it will be merged with the previous
        >>> c2 = Contact()
        >>> c2.name = ["john"]
        >>> c2.telephone = ["911"]
        >>> a.add_contact(c2)

        the updated contact is retrieved
        >>> a.find(name="john").telephone
        ['911']
        >>> a.find(name="john").org
        ['wikipedia']
        >>> len(a.contacts)
        1

        Add a third similar contact, without auto_merge
        >>> c3 = Contact(name="John", telephone="911")
        >>> a.add_contact(c3, auto_merge=False)
        >>> len(a.contacts)
        2


        """
        # todo : encrypt ?
        self._contacts = []

    @property
    def contacts(self):
        # type: () -> list
        return self._contacts

    def add_contact(self, contact, auto_merge=True):
        # type: (Contact, bool) -> None
        if not auto_merge or not len(self.contacts):
            self._contacts.append(contact)
            return

        duplicate = self.find_best_duplicate(contact)
        if duplicate:
            duplicate.merge(contact)
        else:
            self._contacts.append(contact)

    def load_from_file(self):
        save_path = self.get_save_file_path()
        if not os.path.exists(save_path):
            logger.error("Could not load. File {} not found".format(save_path))
            return
        with open(self.get_save_file_path(), 'r') as f_save:
            self._contacts = pickle.load(f_save)

    def save_to_file(self):
        for c in self.contacts:
            c.consolidate()
        with open(self.get_save_file_path(), 'w') as f_save:
            pickle.dump(self._contacts, f_save)

    @staticmethod
    def get_save_file_path():
        path = os.environ.get("XDG_DATA_HOME")
        if path:
            return os.path.join(path, SAVE_FILENAME)
        return os.path.join(os.path.expanduser(ZPUI_HOME), SAVE_FILENAME)

    def find(self, **kwargs):
        # type: (dict) -> Contact
        # simple wrapper around find_best_duplicate
        c = Contact(**kwargs)
        return self.find_best_duplicate(c)

    def find_best_duplicate(self, contact):
        # type: (Contact) -> Contact
        match_score_contact_list = self.find_duplicates(contact)
        if match_score_contact_list[0][0] > 0:
            return match_score_contact_list[0][1]

    def find_duplicates(self, contact):
        # type: (Contact) -> list
        if contact in self._contacts:
            return [1, contact]
        match_score_contact_list = [(c.match_score(contact), c) for c in self.contacts]

        def cmp(a1, a2):
            # type: (tuple, tuple) -> int
            return a1[0] > a2[0]

        return sorted(match_score_contact_list, cmp=cmp)


class Contact(object):
    """
    >>> c = Contact()
    >>> c.name
    []
    >>> c = Contact(name="John")
    >>> c.name
    ['John']
    """

    def __init__(self, **kwargs):
        self.name = []
        self.address = []
        self.telephone = []
        self.email = []
        self.url = []
        self.note = []
        self.org = []
        self.photo = []
        self.title = []
        self.from_kwargs(kwargs)

    def from_kwargs(self, kwargs):
        provided_attrs = {attr: kwargs[attr] for attr in self.get_all_attributes() if attr in kwargs.keys()}
        for attr_name in provided_attrs:
            attr_value = provided_attrs[attr_name]
            if isinstance(attr_value, list):
                setattr(self, attr_name, attr_value)
            else:
                setattr(self, attr_name, [attr_value])

    def match_score(self, other):
        # type: (Contact) -> int
        """
        Computes how many element matches with other and self
        >>> c1 = Contact(name="John", telephone="911")
        >>> c2 = Contact(name="Johnny")
        >>> c1.match_score(c2)
        0
        >>> c2.telephone = ["123", "911"] # now the contacts have 911 in common
        >>> c1.match_score(c2)
        1

        Now add a common nickname to them, ignoring case
        >>> c1.name.append("deepthroat")
        >>> c2.name.append("DeepThroat")
        >>> c1.match_score(c2)
        2
        """
        common_attrs = set(self.get_filled_attributes()).intersection(other.get_filled_attributes())
        return sum([self.common_attribute_count(getattr(self, attr), getattr(other, attr)) for attr in common_attrs])

    def consolidate(self):
        """
        Merge duplicate attributes
        >>> john = Contact()
        >>> john.name = ['John', 'John Doe', '   John Doe', 'Darling']
        >>> john.consolidate()
        >>> 'Darling' in john.name
        True
        >>> 'John Doe' in john.name
        True
        >>> len(john.name)
        2
        >>> john.org = [['whatever org']]
        >>> john.consolidate()
        >>> john.org
        ['whatever org']
        """
        my_attributes = self.get_filled_attributes()
        for name in my_attributes:  # removes exact duplicates
            self.consolidate_attribute(name)

    def get_filled_attributes(self):
        """
        >>> c = Contact()
        >>> c.name = ["John", "Johnny"]
        >>> c.note = ["That's him !"]
        >>> c.get_filled_attributes()
        ['name', 'note']
        """
        return [a for a in dir(self)
                if not callable(getattr(self, a)) and not a.startswith("__") and len(getattr(self, a))]

    def get_all_attributes(self):
        return [a for a in dir(self) if not callable(getattr(self, a)) and not a.startswith("__")]

    def consolidate_attribute(self, attribute_name):
        # type: (str) -> None
        attr_value = getattr(self, attribute_name)
        attr_value = flatten(attr_value)
        attr_value = list(set([i.strip() for i in attr_value if isinstance(i, basestring)]))  # removes exact duplicates

        attr_value[:] = [x for x in attr_value if not self._is_contained_in_other_element_of_the_list(x, attr_value)]

        setattr(self, attribute_name, list(set(attr_value)))

    def merge(self, other):
        # type: (Contact) -> None
        """
        >>> c1 = Contact()
        >>> c1.name = ["John"]
        >>> c2 = Contact()
        >>> c2.name = ["John"]
        >>> c2.telephone = ["911"]
        >>> c1.merge(c2)
        >>> c1.telephone
        ['911']
        """
        attr_sum = self.get_filled_attributes() + other.get_filled_attributes()
        for attr_name in attr_sum:
            attrs_sum = getattr(self, attr_name) + getattr(other, attr_name)
            setattr(self, attr_name, attrs_sum)
        self.consolidate()

    def short_name(self):
        for attr_name in self.get_filled_attributes():
            for attribute in getattr(self, attr_name):
                if not isinstance(attribute, basestring) and not isinstance(attribute, list):
                    continue
                if isinstance(attribute, list):
                    for entry_str in attribute:
                        if not isinstance(entry_str, basestring):
                            continue
                else:
                    return attribute
        return "unknown"

    @staticmethod
    def common_attribute_count(a1, a2):
        # type: (list, list) -> int
        a1_copy = [i.lower() for i in a1 if isinstance(i, basestring)]
        a2_copy = [i.lower() for i in a2 if isinstance(i, basestring)]
        return len(set(a1_copy).intersection(a2_copy))

    @staticmethod
    def _is_contained_in_other_element_of_the_list(p_element, the_list):
        """
        """
        # type: (object, list) -> bool
        copy = list(the_list)
        copy.remove(p_element)
        for element in copy:
            if p_element in element:
                return True
        return False


SAVE_FILENAME = "contacts.pickle"
