from datetime import datetime
from email.mime.text import MIMEText

import random
import requests
import smtplib

import login

DATE_FORMAT_RECORD = "%Y%m%d"
DATE_FORMAT_MSG = "%c"

SIZE_DICT = 72547

URL_DICT = "https://www.le-dictionnaire.com/definition/{word}"

TOs = [
    "fxstempfel@gmail.com"
]

BODY = """
Hello!

Le mot du jour est : {today}
Sa défintion ici : {url}
{history}
A demain !
"""


class EMail:
    def __init__(self, from_user, to, subject, message_text):
        self.from_user = from_user
        self.to = to
        self.subject = subject
        self.message_text = message_text

    def send(self):
        message = MIMEText(self.message_text)
        message["from"] = self.from_user
        message["to"] = self.to
        message["subject"] = self.subject

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
            with open("fr-classique.dic", "r", encoding="utf8") as f:
                for i, line in enumerate(f):
                    if i == nb_line and WordPicker.check_word_ok(line):
                        return line.split("/")[0]

    @staticmethod
    def check_word_ok(line):
        if not ("po:nom" in line or "po:adj" in line or "po:infi" in line or "po:v" in line):
            return False

        word = line.split("/")[0]

        r = requests.get(URL_DICT.format(word=word))
        if r.status_code != 200:
            return False

        return "<h3>Définition de {}</h3>".format(word) in r.content.decode("utf8")


class Master:
    @staticmethod
    def update_record(word):
        try:
            with open("record.txt", "r") as f:
                lines = f.readlines()
                nb_words = len(lines)
        except FileNotFoundError:
            nb_words = 0
            lines = []

        date = datetime.now().strftime(DATE_FORMAT_RECORD)
        new_line = "{}:{}\n".format(date, word)
        with open("record.txt", "w") as f:
            f.write(new_line)
            for line in lines[:min(nb_words, 7)]:
                f.write(line)

    @staticmethod
    def read_record():
        try:
            with open("record.txt", "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            return {}

        res = {}
        for line in lines:
            date, word = line.split(":")
            res[datetime.strptime(date, DATE_FORMAT_RECORD).strftime(DATE_FORMAT_MSG)] = word.strip("\n")
        return res

    @staticmethod
    def format_email(word):
        try:
            history = "\n" \
                      + "\n".join(["{} : {}\t{}".format(date, old_word, URL_DICT.format(word=old_word))
                                   for date, old_word in Master.read_record().items()]) \
                      + "\n"
        except AttributeError:
            history = ""
        except ValueError:
            print(Master.read_record())
            raise ValueError

        body = BODY.format(today=word, url=URL_DICT.format(word=word), history=history)

        return body

    @staticmethod
    def main():
        new_word = WordPicker.pick()
        message_text = Master.format_email(new_word)

        for to in TOs:
            EMail("Daily Word", to, "Le Mot du Jour", message_text).send()

        Master.update_record(new_word)


if __name__ == '__main__':
    Master.main()
    # TODO format date
