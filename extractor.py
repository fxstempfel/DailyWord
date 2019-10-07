"""
To extract words from websites into a JSON file which lists all of them as well as their definitions and perhaps links
to wiktionary.
"""
import json
import re
import requests
import xlrd

from lxml import etree
from bs4 import BeautifulSoup

URL_JOLIS_MOTS = "https://jolismots.fr/dictionnaire/"
URL_WEB_NEXT = "https://webnext.fr/langue-francaise"
URL_WEB_NEXT_BASE = "https://webnext.fr"
URL_LAROUSSE_BASE = "https://larousse.fr/dictionnaires/francais/"
URL_WIKI_BASE = "https://fr.wiktionary.org/wiki/"

JSON_PATH = "words.json"


class NotFoundError(Exception):
    pass


def get_def_from_wiki(word):
    """We need to get:
    1. word definitions + examples
    2. type (nom commun féminin etc)
    3. conj link if verb"""
    uri = URL_WIKI_BASE + word
    r = requests.get(uri)

    if r.status_code != 200:
        print(f'{word}: code {r.status_code}')
        raise NotFoundError

    soup = BeautifulSoup(r.content, 'html.parser')

    # retrieve type
    try:
        word_type = soup.find('span', attrs={'class': 'titredef'}).text.lower().strip(' 1')
    except AttributeError:
        word_type = None

    if 'nom commun' in word_type:
        try:
            gender = soup.find('span', attrs={'class': 'ligne-de-forme'}).text.lower()
            word_type = '{} {}'.format(word_type.replace(' commun', ''), gender)
        except AttributeError:
            pass

    # retrieve conj link
    if 'verbe' in word_type:
        try:
            conjugation_link = soup.find('a', attrs={'title': f'Annexe:Conjugaison en français/{word}'})['href']
            conjugation_link = URL_WIKI_BASE + conjugation_link[1:]  # remove leading '/'
        except TypeError:
            conjugation_link = None
    else:
        conjugation_link = None

    # retrieve definitions and examples
    definitions = []
    for definition in soup.find('ol').findAll('li', recursive=False):
        # is there a sublist of definitions?
        # sometimes there's an extra hierarchy 1.a/b/c etc (see râble)
        def_sublist = definition.findAll('li')
        for elem in def_sublist:
            if len(elem.findAll('li')) > 0:
                # too complex
                print(f'{word} sublist found')
                raise NotFoundError

        # get meaning
        all_text = definition.get_text()
        try:
            text_examples = definition.find('ul').get_text()
        except AttributeError:
            text_examples = ''

        # remove examples from meaning
        meaning = all_text.replace(text_examples, '').replace('\xa0', ' ').strip(' \n')

        references = definition.findAll('sup', attrs={'class': 'reference'})
        for ref in references:
            meaning = meaning.replace(ref.text, '')

        # get precisions (allow a 2-letter word between successive precisions)
        match = re.match(r'^( ?\w{0,2} ?\(\w+\))*', meaning).group(0)  # extract words between parentheses at the beginning
        if len(match) > 0:
            meaning = meaning.replace(match, '').strip(' ();,')
            def_precisions = [x.group().strip('()') for x in re.finditer(r'(\(\w+\))', match)]
            if len(def_precisions) == 0:
                def_precisions = None
        else:
            def_precisions = None

        if text_examples == '':
            definitions.append({
                'meaning': meaning,
                'examples': None,
                'precisions': def_precisions
            })
            continue

        # get examples
        examples = []
        for example in definition.findAll('li'):
            # extract sources
            sources_span = example.find('span', attrs={'class': 'sources'})
            if sources_span is None:
                example_author = None
                example_work = None
            else:
                sources = sources_span.extract()

                # get author
                example_author = sources.find('a', attrs={'class': 'extiw'})
                if example_author is not None:
                    example_author = example_author.get_text().replace('\xa0', ' ').strip(' \n,;:')

                # get work
                try:
                    example_work = sources.find('i').get_text().replace('\xa0', ' ').strip(' \n,;:')
                except AttributeError:
                    example_work = None

            # get example text
            #example_i = example.findAll('i')
            try:
                #example_text = example_i[0].get_text().replace('\xa0', ' ').strip(' \n,;:')
                example_text = example.get_text().replace('\xa0', ' ').strip(' \n,;:')
            except IndexError:
                print(f'no <i> for {word}')
                continue

            if example_text is None:
                continue

            examples.append({
                'text': example_text,
                'author': example_author,
                'work': example_work
            })

        if len(examples) == 0:
            examples = None

        definitions.append({'meaning': meaning, 'examples': examples, 'precisions': def_precisions})

    word_info = {
        'name': word,
        'type': word_type,
        'conjugation_link': conjugation_link,
        'definitions': definitions,
        'link': uri
    }

    return word_info


# TODO explore cnrtl instead of larousse
def get_def_from_larousse(word):
    """Return definition from Larousse or None if not found"""
    uri = URL_LAROUSSE_BASE + word
    r = requests.get(uri)

    if r.status_code != 200:
        raise NotFoundError

    soup = BeautifulSoup(r.content, 'html.parser')

    # find type
    try:
        word_type = soup.find("p", attrs={'class': "CatgramDefinition"}).text.replace("CONJUGAISON", "").strip()
    except AttributeError:
        word_type = None

    # if it's a verb find the link to its conjugation tables
    if word_type is not None and "verbe" in word_type:
        try:
            link = soup.find('a', attrs={'class': 'lienconj'})['href']
            conjugation_link = "http://larousse.fr{}".format(link) if link is not None else None
        except TypeError:
            print(f'no link for {word}')
            conjugation_link = None
    else:
        conjugation_link = None

    # find all definitions
    all_definitions = []
    for definition in soup.find_all("li", attrs={'class': 'DivisionDefinition'}):
        meaning = definition.get_text().replace('\xa0', ' ')

        try:
            definition_field = definition.find('p', attrs={'class': 'RubriqueDefinition'}).get_text()
            meaning = meaning.replace(definition_field, '')
        except AttributeError:
            definition_field = None

        # find example
        example_def = definition.find("span", attrs={"class": 'ExempleDefinition'})
        if example_def is not None:
            example_text = example_def.string
            if example_text is not None:
                meaning = meaning.replace(example_text, '').replace('\xa0', ' ').strip(' :')
            else:
                meaning = meaning.replace('\xa0', ' ').strip(' :')
        else:
            example_text = None

        example = {'text': example_text, 'author': None, 'work': None} if example_text is not None else None
        all_definitions.append({
            "meaning": meaning,
            "examples": example,
            'precisions': [definition_field] if definition_field is not None else None
        })

    print(f'{word} done by Larousse')

    return {"name": word, "definitions": all_definitions, "type": word_type, "conjugation_link": conjugation_link, 'link': uri}


def get_words_from_webnext(size=None):
    all_words = []
    r = requests.get(URL_WEB_NEXT)
    root = etree.HTML(r.content)
    for href in set(root.xpath("//a[contains(@href, 'page=')]/@href")):
        uri = URL_WEB_NEXT_BASE + href
        r = requests.get(uri)
        root_page = etree.HTML(r.content)
        all_words += [x.text.lower()
                      for x in root_page.xpath("//div[@class='pull-left']/h4/span[@class='label label-primary']")
                      if " " not in x.text and "-" not in x.text and x.text[0] == x.text[0].lower()]
        if size is not None and len(all_words) >= size:
            break

    # read most frequent words to remove them from list
    sheet = xlrd.open_workbook('liste_frequence_des_mots.xls').sheets()[0]
    most_used_words = sheet.col_values(2)[1:]
    words_before = all_words.copy()
    all_words = list(set(all_words) - set(most_used_words))
    print('removed', set(words_before) - set(all_words))

    return all_words


def make_json(n_words=None):
    word_list = get_words_from_webnext(n_words)
    print('found', len(word_list), 'words')
    word_dict = {"words": []}
    for w in word_list:
        try:
            word_object = get_def_from_wiki(w)
        except NotFoundError:
            try:
                word_object = get_def_from_larousse(w)
            except NotFoundError:
                continue
        if len(word_object['definitions']) > 0:
            word_dict["words"].append(word_object)

    with open(JSON_PATH, "w", encoding="utf8") as f:
        f.write(json.dumps(word_dict, indent=True, ensure_ascii=False))


# TODO http://golfes-dombre.nuxit.net/mots-rares/a.html
# http://golfes-dombre.nuxit.net/mots-rares/a.html
# use pypdf2 maybe https://medium.com/@rqaiserr/how-to-convert-pdfs-into-searchable-key-words-with-python-85aab86c544f
# or better tika https://stackoverflow.com/questions/34837707/how-to-extract-text-from-a-pdf-file


if __name__ == '__main__':
    make_json()
