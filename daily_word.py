from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import locale
import random
import requests
import smtplib

import login

DATE_FORMAT_RECORD = "%Y%m%d"
DATE_FORMAT_MSG = "%A %d %B"

SIZE_DICT = 22740

URL_DICT = "https://www.le-dictionnaire.com/definition/{word}"

PATH_DICT = "liste_francais.txt"
PATH_RECORD = "record.txt"

SUBJECT = "Le Mot du Jour"
TOs = [
    "fxstempfel@gmail.com"
]

BODY = """
<html>
<h1>Le Mot du Jour</h1>

<p>Le mot du jour est : <a href="{url}">{today}</a></p>
<p>{history}</p>
<p>À demain !</p>
</html>
"""


class EMail:
    def __init__(self, from_user, to, subject, message_text):
        self.from_user = from_user
        self.to = to
        self.subject = subject
        self.message_text = message_text

    def send(self):
        message = MIMEMultipart("alternative")
        html_part = MIMEText(self.message_text, "html")
        message["from"] = self.from_user
        message["to"] = self.to
        message["subject"] = self.subject

        message.attach(html_part)

        server = smtplib.SMTP("smtp.office365.com", 587)
        server.ehlo()
        server.starttls()
        server.login(login.user, login.password)
        server.sendmail(login.user, self.to, message.as_string())
        server.close()


class WordPicker:
    @staticmethod
    def pick():
        while True:
            nb_line = random.randint(0, SIZE_DICT)
            print(nb_line)
            with open(PATH_DICT, "r") as f:
                for i, line in enumerate(f):
                    word = line.strip("\n")
                    if i == nb_line and WordPicker.check_word_ok(word):
                        return word

    @staticmethod
    def check_word_ok(word):
        r = requests.get(URL_DICT.format(word=word))
        if r.status_code != 200:
            return False

        return "<h3>Définition de {}</h3>".format(word) in r.content.decode("utf8")


class Master:
    @staticmethod
    def update_record(word):
        try:
            with open(PATH_RECORD, "r") as f:
                lines = f.readlines()
                nb_words = len(lines)
        except FileNotFoundError:
            nb_words = 0
            lines = []

        date = datetime.now().strftime(DATE_FORMAT_RECORD)
        new_line = "{}:{}\n".format(date, word)
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
            date, word = line.split(":")
            res[datetime.strptime(date, DATE_FORMAT_RECORD).strftime(DATE_FORMAT_MSG)] = word.strip("\n")
        return res

    @staticmethod
    def format_email(word, to):
        dict_old = Master.read_record()
        if len(dict_old) == 0:
            history = ""
        else:
            try:
                history = "Petit rappel des derniers mots :" \
                          + "\n".join(['<li>{} : <a href="{}">{}</a></li>'.format(date, URL_DICT.format(word=old_word), old_word)
                                       for date, old_word in dict_old.items()]) \
                          + "\n"
            except AttributeError:
                history = ""
            except ValueError:
                print(Master.read_record())
                raise ValueError

        body = BODY.format(to=to,
                           subject=SUBJECT,
                           today=word,
                           url=URL_DICT.format(word=word),
                           history=history)

        return body

    @staticmethod
    def main():
        new_word = WordPicker.pick()

        locale.setlocale(locale.LC_ALL, 'fr_FR.utf8')

        for to in TOs:
            message_text = Master.format_email(new_word, to)
            EMail("Daily Word", to, SUBJECT, message_text).send()

        Master.update_record(new_word)


if __name__ == '__main__':
    Master.main()
