import parser
import tone_center
import chord_center
import key_sig
import term_print
import os
import pandas as pd


# Key Dict
index_key_dict = {
    'C': 1,
    'Db': 2,
    'D': 3,
    'Eb': 4,
    'E': 5,
    'F': 6,
    'Gb': 7,
    'G': 8,
    'Ab': 9,
    'A': 10,
    'Bb': 11,
    'B': 12
}

# Scale Tone Weights with integer keys
# [ REDACTED ]

# Chord Tone Weights with float keys
# [ REDACTED ]

# offsets for each column scale value
offsets = {
    'C': 0,    # 00 -> 1, 01 -> 2, ..., 7F -> 12
    'Db': 11,  # 00 -> 12, 01 -> 1, ..., 7F -> 11
    'D': 10,   # etc.
    'Eb': 9,   
    'E': 8,    
    'F': 7,    
    'Gb': 6,   
    'G': 5,    
    'Ab': 4,  
    'A': 3,    
    'Bb': 2,   
    'B': 1     
}

# Define mode intervals: how many note steps away is a Mode's key who shares key signature with Major Scale
# (for example: C Major shares key signature with D Dorian)
mode_intervals = {
    0: 'Ionian (Major)',
    2: 'Dorian',
    4: 'Phrygian',
    5: 'Lydian',
    7: 'Mixolydian',
    9: 'Aeolian (Minor)',
    11: 'Locrian'
}

weighted_7chords = {
    "Major 7th": {
        "Weights": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1],
        "Modes": ["Ionian", "Lydian"],
        "Triad": "Major",
        "7th Chords": "Major 7th",
        "Shorthand": "maj7"
    },
    "Dominant 7th": {
        "Weights": [1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0],
        "Modes": ["Mixolydian"],
        "Triad": "Major",
        "7th Chords": "Dominant 7th",
        "Shorthand": "7"
    },
    "Minor 7th": {
        "Weights": [1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
        "Modes": ["Aeolian", "Dorian", "Phrygian"],
        "Triad": "Minor",
        "7th Chords": "Minor 7th",
        "Shorthand": "m7"
    },
    "Diminished 7th": {
        "Weights": [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0],
        "Modes": ["Locrian"],
        "Triad": "Diminished",
        "7th Chords": "Minor ø7",
        "Shorthand": "ø7"
    }
}


if __name__ == "__main__":
    
    ''' place to enter song name '''
    songname = 'song_title_without_extension'
    
    
    ''' parse midi file '''
    # initial reading of midi file, saving of variables and events
    formatted_songname = songname.replace('_', ' ').replace('-', ' ').title()
    print(f'\nFilename: {formatted_songname}')
    midi = os.path.join('midiFiles', f'{songname}.mid')  # MIDI file path
    parsed_events, ticks_per_beat, beats_per_measure, beat_values, tempos, min_rest = parser.parse_midi(midi)

    
    ''' process from raw parsed midi through key signature weights 
        with saving points along the way to csv'''
    # raw midi
    parsed_csv = os.path.join('csv', f'{songname}1_parsed_events.csv')
    csv = parser.save_parsed_events_to_csv(parsed_events, parsed_csv)
    
    # legible midi with added note information
    notes_csv = os.path.join('csv', f'{songname}2_notes.csv')
    df = parser.csv_to_dataframe(csv, notes_csv)
    
    # legible midi with measure calculations
    measures_csv = os.path.join('csv', f'{songname}3_measures.csv')
    df, df_time_sig = parser.measure_calculations(df, ticks_per_beat, beats_per_measure, beat_values)
    parser.round_to_csv(df, measures_csv)
    
    # split spanning measures in new df
    # ... 
    
    '''
    
    [ PROPRIETARY ]
    
    '''
