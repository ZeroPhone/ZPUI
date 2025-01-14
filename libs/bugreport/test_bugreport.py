import os
import zipfile
import unittest
from mock import Mock

from libs.bugreport.bugreport import BugReport


class TestBugReport(unittest.TestCase):

    def test_workflow_without_send(self):
        br = BugReport("test.zip")
        br.add_dir_or_file("__init__.py")
        br.add_dir_or_file("resources/")
        br.add_text("print('Hello')", "main.py")
        # Let's test if the resulting file is a ZIP file
        br.zip.close()
        br.zip_contents.seek(0)
        assert(zipfile.is_zipfile(br.zip_contents))
        # The file *might* be massive if we've packed the entire ZPUI directory by some chance
        del br.zip_contents
        del br.zip

    def test_save_in(self):
        br = BugReport("zpui_bugreport_test.zip")
        br.add_dir_or_file("__init__.py")
        br.store_in("/tmp")
        assert(os.path.isfile("/tmp/zpui_bugreport_test.zip"))
        # Test if the resulting file is a ZIP file
        assert(zipfile.is_zipfile("/tmp/zpui_bugreport_test.zip"))
        os.remove("/tmp/zpui_bugreport_test.zip")

if __name__ == "__main__":
    unittest.main()
