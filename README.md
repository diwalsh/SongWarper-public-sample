# SongWarper: Public Sample
Sample python scripts from Song Warper Project for Public Viewing

---
### Overview of Song Warper 
Song Warper is a collaborative machine learning project for musicians and songwriters. In it's current iteration, it accepts a `.mid/.midi file`, provided by a user, of a melody in its whole or in part. The user is able to select the genre, among several other specifications. Song Warper analyzes the MIDI file, determining the tonal center, key signatures, time signatures, and chord progressions of the melody provided by the user. It then writes accompaniment to the melody, with various instrument parts, using its detailed analysis. Each written accompaniment is unique, so the user may run the program as many times as desired to receive a variety of options. In later iterations, Song Warper will be able to complete this entire process, based on user inputted specifications, without the user-provided melody. 

### Included in this Sample:
This public repository contains two files: `parser.py` and `runner.py`. \n
`runner.py` contains the main script of the project, calling on several python files written with helper functions: 
`* parser.py
* tone_center.py
* key_sig.py
* chord_center.py
* term_print.py`

`parser.py` is also included, which contains the scripts for parsing the raw `.mid/.midi file` provided by the user. It uses `pandas DataFrames` to switch back and forth between analysis and printing to `.csv` files, plus terminal read outs of discoveries. 
