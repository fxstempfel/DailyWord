import json
import os

from google.cloud import firestore


# authenticate
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'DailyWord-af0f3f381976.json'

# connect to Firebase
db = firestore.Client()
collection = db.collection('dictionary')

# read words
with open('words.json', 'r', encoding='utf-8') as f:
    words_list = json.load(f)['words']

# upload words
for word in words_list[:10]:
    doc_ref = collection.document(word['name'])
    doc_ref.set(word)
