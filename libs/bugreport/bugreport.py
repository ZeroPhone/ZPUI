from ftplib import FTP_TLS as FTP
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO
from mock import Mock
import traceback
import zipfile
import ssl
import os

class BugReport(object):

    ftp_destination = "ftp.zerophone.org"

    def __init__(self, filename):
        self.zip_contents = StringIO()
        self.zip_contents.name = filename
        self.zip = zipfile.ZipFile(self.zip_contents, mode="w", compression=zipfile.ZIP_DEFLATED)

    def add_file(self, path):
        self.zip.write(path)

    def add_dir(self, path):
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                self.add_file(file_path)

    def add_dir_or_file(self, path):
        if os.path.isfile(path):
            self.add_file(path)
        elif os.path.isdir(path):
            self.add_dir(path)
        else:
            raise ValueError("{} is neither file nor directory!".format(path))

    def add_text(self, text, filename):
        self.zip.writestr(filename, text)

    def send_or_store(self, path, logger=Mock()):
        try:
            self.send()
            return [True, self.ftp_destination]
        except Exception as e:
            logger.exception("Failed to send to {}!".format(self.ftp_destination))
            bugreport.add_text(json.dumps(traceback.format_exc()), "bugreport_sending_failed.json")
            location = self.store_in(path)
            logger.error("Stored in {}".format(location))
            return [False, location]

    def store_in(self, path):
        full_path = os.path.join(path, self.zip_contents.name)
        self.zip.close()
        self.zip_contents.seek(0)
        with open(full_path, 'w') as f:
            f.write(self.zip_contents.read())
        return full_path

    def send(self):
        ftp = FTP(self.ftp_destination)
        ftp.set_debuglevel(2)
        ftp.ssl_version = ssl.PROTOCOL_TLSv1_2
        ftp.login()
        ftp.cwd("upload")
        ftp.prot_p()
        self.zip.close()
        self.zip_contents.seek(0)
        ftp.storbinary("STOR {}".format(self.zip_contents.name), self.zip_contents)


if __name__ == "__main__":
    filename = "zpui_bootlog_test.zip"
    report = BugReport(filename)
    report.add_file('config.json')
    report.add_text('"this is a description text"', 'description.json')
    report.send()
