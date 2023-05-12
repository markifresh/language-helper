### Language helper
#### This project app takes a list of words and: 

- uses chatGPT to set for each word
  - translation
  - check if word is exception
  - creates useful sentence (with translation)
  - set category for word
- uses MS Azure to create audio for each word and sentence
- sets Anki tags
- converts words list to csv file
---
The project has modified Anki cards (use <body> of files):
- replaces the default audio with HTML audio
- custom source of audio in HTML audio
- use audio in cards without modifying cards <br>
  (will add audio based on card content)
- custom spell check, which also works in web (default doesn't work)
- custom input fields
---
With this app you can create csv file with words and audio for them.<br>
1. Create card type in Anki, using html files of anki_cards/<br>
2. Create deck in Anki and import there CSV file, using new cards type<br>
3. Copy to anki collection folder:
   - audio files
   - anki_cards/_collections.css
   - anki_cards/_scripts.js


4. Now you have
   - csv file with words
   - audio for all words and phrases
   - Anki cards of all that words with audios and tags 
