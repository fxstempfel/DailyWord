"""
To extract words from websites into a JSON file which lists all of them as well as their definitions and perhaps links
to wiktionary.
"""
import json
import requests

from lxml import etree
from bs4 import BeautifulSoup

URL_JOLIS_MOTS = "https://jolismots.fr/dictionnaire/"
URL_WEB_NEXT = "https://webnext.fr/langue-francaise"
URL_WEB_NEXT_BASE = "https://webnext.fr"
URL_LAROUSSE_BASE = "https://larousse.fr/dictionnaires/francais/"

JSON_PATH = "words.json"


def check_definition(word):
    """Return definition from Larousse or None if not found"""
    uri = URL_LAROUSSE_BASE + word
    r = requests.get(uri)

    soup = BeautifulSoup(r.content, 'html.parser')

    # find type
    try:
        word_type = soup.find("p", attrs={'class': "CatgramDefinition"}).text.replace("CONJUGAISON", "").strip()
    except AttributeError:
        word_type = None

    # if it's a verb find the link to its conjugation tables
    if word_type is not None and "verbe" in word_type:
        link = soup.find('a', attrs={'class': 'lienconj'})['href']
        conjugation_link = "http://larousse.fr{}".format(link) if link is not None else None
    else:
        conjugation_link = None

    # find all definitions
    all_definitions = []
    for definition in soup.find_all("li", attrs={'class': 'DivisionDefinition'}):
        meaning = definition.get_text()

        # find example
        example = definition.find("span", attrs={"class": 'ExempleDefinition'})
        if example is not None:
            example = example.string
            meaning = meaning.replace(example, '').strip('\xa0 :')

        all_definitions.append({
            "meaning": meaning,
            "example": example,
        })

    return {"name": word, "definitions": all_definitions, "type": word_type, "conjugation_link": conjugation_link}


def parse_web_next(size=None):
    all_words = []
    r = requests.get(URL_WEB_NEXT)
    root = etree.HTML(r.content)
    for href in set(root.xpath("//a[contains(@href, 'page=')]/@href")):
        uri = URL_WEB_NEXT_BASE + href
        r = requests.get(uri)
        root_page = etree.HTML(r.content)
        all_words += [x.text.lower()
                      for x in root_page.xpath("//div[@class='pull-left']/h4/span[@class='label label-primary']")
                      if " " not in x.text]
        if size is not None and len(all_words) >= size:
            break
    return all_words


def make_json():
    word_list = parse_web_next(20)
    print('found', len(word_list), 'words')
    word_dict = {"words": []}
    for w in word_list:
        word_object = check_definition(w)
        if len(word_object["definitions"]) > 0:
            word_dict["words"].append(word_object)

    with open(JSON_PATH, "w", encoding="utf8") as f:
        f.write(json.dumps(word_dict, indent=True, ensure_ascii=False))

# TODO http://golfes-dombre.nuxit.net/mots-rares/a.html
# http://golfes-dombre.nuxit.net/mots-rares/a.html
# use pypdf2 maybe https://medium.com/@rqaiserr/how-to-convert-pdfs-into-searchable-key-words-with-python-85aab86c544f
# or better tika https://stackoverflow.com/questions/34837707/how-to-extract-text-from-a-pdf-file


if __name__ == '__main__':
    make_json()
