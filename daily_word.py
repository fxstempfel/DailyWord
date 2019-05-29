from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from lxml import etree

import locale
import random
import requests
import smtplib
import string

import login

DATE_FORMAT_RECORD = "%Y%m%d"
DATE_FORMAT_MSG = "%A %d %B"

URL_BASE = "https://www.le-dictionnaire.com"

PATH_RECORD = "record.txt"

SUBJECT = "Le Mot du Jour"
TOs = [
    "fxstempfel@gmail.com"
]

URL_LETTER = "https://www.le-dictionnaire.com/repertoire/{letter}01.html"

BODY = """
<html>
<h1>Le Mot du Jour</h1>

<p>Le mot du jour est : <a href="{url}">{today}</a></p>
<p>{history}</p>
<p>À demain !</p>
</html>
"""


class EMail:
    @staticmethod
    def send(from_user, to, subject, message_text):
        message = MIMEMultipart("alternative")
        html_part = MIMEText(message_text, "html")
        message["from"] = from_user
        message["to"] = to
        message["subject"] = subject

        message.attach(html_part)

        server = smtplib.SMTP("smtp.office365.com", 587)
        server.ehlo()
        server.starttls()
        server.login(login.user, login.password)
        server.sendmail(login.user, to, message.as_string())
        server.close()


class PartFormatter:
    def __init__(self, language):
        self.language = language
        self.word = None
        self.url = None

    def pick(self):
        if self.language == "fr":
            letter = random.choice(string.ascii_letters)
            print("LETTRE", letter)
            response = requests.get(URL_LETTER.format(letter=letter))
            root = etree.HTML(response.content)
            print(etree.tostring(root, pretty_print=True, encoding="unicode"))
            selected_range = random.choice(root.xpath("//span[div[@class='titregroupelettre']]/a")).attrib["href"]

            response = requests.get(URL_BASE + selected_range)
            root = etree.HTML(response.content)
            list_words_a = root.xpath("//div[@class='alphabox']/ul/li/a")
            word_a = random.choice(list_words_a)
            self.word, self.url = word_a.text, URL_BASE + word_a.attrib["href"]
        elif self.language == "en":
            pass

    def format_part(self):
        #TODO format a language specific part of email + in master format whole email from scratch
        pass


class Master:
    @staticmethod
    def update_record(word, url_word):
        try:
            with open(PATH_RECORD, "r") as f:
                lines = f.readlines()
                nb_words = len(lines)
        except FileNotFoundError:
            nb_words = 0
            lines = []

        date = datetime.now().strftime(DATE_FORMAT_RECORD)
        new_line = "{}##{}##{}\n".format(date, word, url_word)
        with open(PATH_RECORD, "w") as f:
            f.write(new_line)
            for line in lines[:min(nb_words, 7)]:
                f.write(line)

    @staticmethod
    def read_record():
        try:
            with open(PATH_RECORD, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return {}

        res = {}
        for line in lines:
            date, word, url = line.split("##")
            res[datetime.strptime(date, DATE_FORMAT_RECORD).strftime(DATE_FORMAT_MSG)] = word, url.strip("\n")
        return res

    @staticmethod
    def format_email(word, url, to):
        dict_old = Master.read_record()
        if len(dict_old) == 0:
            history = ""
        else:
            try:
                history = "Petit rappel des derniers mots :" \
                          + "\n".join(['<li>{} : <a href="{}">{}</a></li>'.format(date, old_url, old_word)
                                       for date, (old_word, old_url) in dict_old.items()]) \
                          + "\n"
            except AttributeError:
                history = ""
            except ValueError:
                print(Master.read_record())
                raise ValueError

        body = BODY.format(to=to,
                           subject=SUBJECT,
                           today=word,
                           url=url,
                           history=history)

        return body

    @staticmethod
    def main():
        fr_formatter = PartFormatter("fr")
        fr_formatter.pick()
        new_word, url = fr_formatter.word, fr_formatter.url

        locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

        for to in TOs:
            message_text = Master.format_email(new_word, url, to)
            EMail.send("Daily Word", to, SUBJECT, message_text)

        Master.update_record(new_word, url)


if __name__ == '__main__':
    Master.main()
