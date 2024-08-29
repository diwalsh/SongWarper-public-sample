import mido
import csv
import pandas as pd
from fractions import Fraction
import math
import term_print

class NoneHandlingDictWriter(csv.DictWriter):
    ''' class to handle conversion of None values to explicit 'None' string '''
    def writerow(self, rowdict):
        row = {k: v if v is not None else 'None' for k, v in rowdict.items()}
        return super().writerow(row)


def parse_midi(filename):
    ''' function to load/read Midi file via Mido:
        determine all time signature and tempos, if and where they change, 
        pass all events to a helper file to parse event details into dicts,
        return parsed events as a list of dicts, time signature & tempo returned as 
        lists of tuple(s) (with time sig numerator/denominator separated), 
        where each tuple is an instance of time sig/tempo and where it begins,
        ticks per beat and minimum rest as singular variables '''
        
    # load/read MIDI file via mido
    mid = mido.MidiFile(filename)

    # initializing variables
    parsed_events = [] # list of message events
    tempo_changes, beats_per_measure_changes, beat_value_changes = [], [], [] # list of tuples
    ticksPBeat = mid.ticks_per_beat
    minRest = Fraction(1,64)
    current_tick = 0 # to keep track of cumulative time for tuples!
    
    # iterate through MIDI file
    for track in mid.tracks:
        # iterate through each message
        for msg in track:
            current_tick += msg.time
            
            # getting time signature numerators & denominators as tuples with time
            if msg.type == 'time_signature':
                    beats_per_measure_changes.append((current_tick, msg.numerator))  # store (time, bpm) tuple
                    beat_value_changes.append((current_tick, msg.denominator))  # store (time, bpm) tuple
                    
            # getting tempos as tuples with time         
            if msg.type == 'set_tempo':
                tempo_changes.append((current_tick, mido.tempo2bpm(msg.tempo)))  # Store (time, bpm) tuple
    
            # message events
            elif isinstance(msg, mido.Message):
                event = parse_message(msg, len(parsed_events) + 1)
                parsed_events.append(event)
    
    term_print.initial_midi_info(ticksPBeat, beats_per_measure_changes, beat_value_changes, tempo_changes, minRest)   
                       
    return parsed_events, ticksPBeat, beats_per_measure_changes, beat_value_changes, tempo_changes, minRest


def parse_message(msg, event_id):
    ''' helper function to parse_midi:
        takes an event message and creates a dictionary to store event's relevant information '''
        
    # access the original raw bytes of the message for hex!!
    raw_bytes = msg.bytes()
    status_byte = F"{raw_bytes[0]:02x}"
    
    event = {
        'ID': event_id,
        'Ticks': msg.time,
        'Channel': msg.channel + 1,
        'Control': status_byte,
        'Value': f"{msg.program:02x}" if status_byte == 'c0' else f"{msg.control:02x}" if status_byte == 'b0' else f"{msg.note:02x}",
        'Data': None if status_byte == 'c0' else (f"{msg.velocity:02x}" if status_byte in ('80', '90') else f"{msg.value:02x}")
    } 
    return event


def save_parsed_events_to_csv(parsed_events, filename):
    ''' save list of raw parsed event dictionaries to csv '''
    
    # field names for CSV
    fieldnames = ['ID', 'Ticks', 'Channel', 'Control', 'Value', 'Data']
    
    # writing to csv file
    with open(filename, mode='w', newline='') as csv_file:
        writer = NoneHandlingDictWriter(csv_file, fieldnames=fieldnames)
        # write the header
        writer.writeheader()
        # write the data
        for event in parsed_events:
            writer.writerow(event)
            
        return filename
    
def round_to_csv(df, filename):
    ''' universal function for saving DataFrame to csv with floats rounded to 6 decimals '''
    
    df_rounded = df.copy()
    
    # round numeric columns to 6 decimal places
    numeric_cols = df_rounded.select_dtypes(include='number').columns
    df_rounded[numeric_cols] = df_rounded[numeric_cols].round(6)
    
    df_rounded.to_csv(filename, index=False)
            
            
def csv_to_dataframe(csv, filename):
    ''' read parsed csv file into pandas DataFrame:
        set message row id as index id, name appropriate columns, 
        begin to zip together note on and note off in column copying logic,
        find rest rows (rows where note on doesn't begin at '0' ticks),
        after rests are shuffled into DataFrame, calculate the cumulative "Position Ticks", 
        remove "note on" rows: "note off" now expresses everything needed zipped together,
        return DataFrame.
        Rests are Message ID incremented 'x' on the n.x decimal place, with n being original Message ID '''
    
    # DataFrame of entire parsed Midi
    df = pd.read_csv(csv) # import to DataFrame
    df.set_index('ID', inplace=True) # set message row id as index id
   
    # DataFrame for notes on / off -- filter rows where Control column is '80' or '90'
    df_notes = df[(df['Control'] == '80') | (df['Control'] == '90')].copy()
    df_notes.reset_index(inplace=True) # reset index after filtering
    
    # Renaming columns
    df_notes.rename(columns={'ID': 'Message ID', 'Data': 'Volume On', 'Ticks': 'Length (Ticks)', 'Value': 'Note Value'}, inplace=True)
    # Inserting new columns
    df_notes.insert(1, 'Position (Ticks)', pd.NA)  # adding 'Position (Ticks)' after 'ID'
    df_notes.insert(df_notes.columns.get_loc('Volume On') + 1, 'Volume Off', pd.NA)  # adding 'Volume Off' after 'Volume'
    
    # list to hold new rest rows
    rest_rows = []
    previous_row_volume_on = pd.NA  # initialize previous row's 'Volume On'
  
    # iterate over DataFrame
    for index, row in df_notes.iterrows():   
        # logic for control 90 (note on) -- to create rest rows
        if row['Control'] == '90' and row['Length (Ticks)'] != 0:
            rest_row = {
                'Message ID': row['Message ID'] - 0.9,
                'Position (Ticks)': pd.NA,
                'Length (Ticks)': row['Length (Ticks)'],
                'Control': 80,
                'Note Value': 'REST',
                'Volume On': pd.NA,
                'Volume Off': pd.NA
            }
            rest_rows.append(rest_row)
            # necessary to keep cumulative time accurate, otherwise double counting with rests
            df_notes.at[index, 'Length (Ticks)'] = 0
            
        # logic for control 80 (note off)
        if row['Control'] == '80':
            df_notes.at[index, 'Volume Off'] = row['Volume On']
            df_notes.at[index, 'Volume On'] = previous_row_volume_on
            
        # update previous_row_volume_on for next iteration
        previous_row_volume_on = row['Volume On']
        
    # DataFrame from rest_rows
    new_rows_df = pd.DataFrame(rest_rows)
    # Concatenate rest rows DataFrame
    df_notes = pd.concat([df_notes, new_rows_df], ignore_index=True)
    # Sort by 'Message ID' to maintain order (shuffles rests back in place)
    df_notes = df_notes.sort_values(by='Message ID').reset_index(drop=True)
    # Coerce 'Channel' back to Integer via Int64 to accommodate Rest's NaN values
    df_notes['Channel'] = pd.to_numeric(df_notes['Channel'], errors='coerce').astype('Int64')
    
    # second iteration to input position values, now that rests are shuffled in
    cumulative_time = 0
    for index, row in df_notes.iterrows():
        # summing and filling in cumulative time column values
        df_notes.at[index, 'Position (Ticks)'] = cumulative_time
        cumulative_time += row['Length (Ticks)']
        
    # Drop rows where Control == 90
    df_notes = df_notes[df_notes['Control'] != '90']
    ### --- Do not drop Control Number -- keep type column for note / rest (Reaper needs this) --
    df_notes['Control'] = df_notes['Note Value'].apply(set_control_value)
    df_notes = df_notes.reset_index(drop=True)
    
    # save the notes/rests DataFrame
    df_notes.to_csv(filename, index=False)
    
    #return df
    return df_notes


def set_control_value(note_value):
    ''' helper function to csv_to_dataframe:
        returns value for new column on whether a row is 'Rest' or 'Note' '''
    if note_value == 'REST':
        return 'Rest'
    else:
        return 'Note'
    
    
def measure_calculations(df, ticks_beats, beats_measure, beats_value):
    ''' creates columns for storing time signature values and Measure index information:
        iterates over DataFrame, measuring the "Measure Index" at beginning of each note
        (depending on the note's initial Beats per Measure value), by incrementing Measure Indexes
        based on the cumulative length of notes being played and local Beats per Value within file. 
        adjustments made for notes played at the same time, to ensure cumulative time is correct.
        it calls a "time signature DataFrame" creating helper function, and returns both DataFrames.'''
        
    # initialize columns with NaN values
    df['Measure Location'] = pd.NA
    df['Measure Duration'] = pd.NA
    df['Beats per Measure'] = pd.NA
    df['Beat Value'] = pd.NA
    
    # initialize variables
    current_measure_index = 0
    ticks_per_measure = ticks_beats * beats_measure[current_measure_index][1] * (4 / beats_value[current_measure_index][1])
    measure_location = 1.0 
    max_measure_index = 0
    
    # iterate over DataFrame
    for index, row in df.iterrows():
        note_start = row['Position (Ticks)']
        note_length = row['Length (Ticks)']
        note_end = note_start + note_length
        
        # set the measure location before adjusting for time signature changes
        df.at[index, 'Measure Location'] = measure_location
        
        # initialize remaining ticks to the entire initial note length
        remaining_ticks = note_length
        # initialize measure duration to begin at 0
        total_measure_duration = 0
        
        # save the time signature (bpm/beat value) for the starting position of the note
        initial_beats_per_measure = beats_measure[current_measure_index][1]
        initial_beat_value = beats_value[current_measure_index][1]
        
        # adjust for time signature changes within the note's duration
        while remaining_ticks > 0 and (current_measure_index + 1 < len(beats_measure) and note_end >= beats_measure[current_measure_index + 1][0]):
            next_change_tick = beats_measure[current_measure_index + 1][0]
            ticks_in_current_measure = next_change_tick - note_start
            
            # check if the remaining ticks of the note fit within the current measure segment
            if ticks_in_current_measure > remaining_ticks:
                ticks_in_current_measure = remaining_ticks
            
            # calculate the proportion of the note in the current measure
            duration_in_current_measure = ticks_in_current_measure / ticks_per_measure
            total_measure_duration += duration_in_current_measure
            
            # move to the next measure index and update ticks per measure
            current_measure_index += 1
            ticks_per_measure = ticks_beats * beats_measure[current_measure_index][1] * (4 / beats_value[current_measure_index][1])
            
            # set the start of the note for the next measure segment
            remaining_ticks -= ticks_in_current_measure
            note_start = next_change_tick
        
        # handle the remaining portion of the note in the current measure
        duration_in_current_measure = remaining_ticks / ticks_per_measure
        total_measure_duration += duration_in_current_measure
        df.at[index, 'Measure Duration'] = total_measure_duration
        df.at[index, 'Beats per Measure'] = initial_beats_per_measure
        df.at[index, 'Beat Value'] = initial_beat_value
        
        # update measure location for the next note
        measure_location += total_measure_duration
        # update the highest measure index
        max_measure_index = max(max_measure_index, int(math.ceil(measure_location)))
    
    # make chord adjustments (so they don't mess up cumulative time)
    df = chord_adjustment(df)
    
    # change data types of specific columns
    df['Position (Ticks)'] = df['Position (Ticks)'].astype(int)
    df['Measure Location'] = df['Measure Location'].astype(float)
    df['Measure Duration'] = df['Measure Duration'].astype(float)
    
    # call time_signature_dict() to get the "measured time signature DataFrame"
    time_sig_df = time_signature_df(max_measure_index, ticks_beats, beats_measure, beats_value)
    
    return df, time_sig_df


def chord_adjustment(df):
    ''' helper function for notes which are played at the same time to inherit certain lost 
        characteristics of the note being played before it.
        
        Note: Due to the logic of how Midi files are written, and then parsed, chords are tricky! 
        example: 
            607,0,1,90,32,58            # Note 32 on at 0 (so, immediately after last message)
            608,0,1,90,39,58            # Note 39 on at 0 (so, immediately after last message)
            609,0,1,90,3e,58            # Note 3e on at 0 (so, immediately after last message)
            610,0,1,90,42,58            # Note 42 on at 0 (so, immediately after last message)
            611,14400,1,80,32,00        # Note 32 off at 14400 (so, 14400 ticks after last message)
            612,0,1,80,39,00            # Note 39 off at 0 (so, immediately after last message)
            613,0,1,80,3e,00            # Note 3e off at 0 (so, immediately after last message)
            614,0,1,80,42,00            # Note 42 off at 0 (so, immediately after last message)
        we can understand that notes 39, 3e and 42 are also turning off at 14400, but in linear midi they 
        must be written as though they are turning at 0 -- when this goes through the logic of the parser, 
        it unfortunately returns the length of the note to be 0 instead of 14400.
        
        Currently, this is a fine fix for chords which play all their notes for the same amount of time.
        However, will need to be made more robust to handle cases where some notes are let off earlier.'''
        
    # iterate through dataframe
    for index in range(1, len(df)):  # Start from 1 (not 0) to avoid IndexError for the first row
        if df.at[index, 'Length (Ticks)'] == 0:
            # Inherit values from the previous row
            df.at[index, 'Length (Ticks)'] = df.at[index - 1, 'Length (Ticks)']
            df.at[index, 'Position (Ticks)'] = df.at[index - 1, 'Position (Ticks)']
            df.at[index, 'Volume On'] = df.at[index - 1, 'Volume On']
            df.at[index, 'Measure Location'] = df.at[index - 1, 'Measure Location']
            df.at[index, 'Measure Duration'] = df.at[index - 1, 'Measure Duration']
    return df


def time_signature_df(total_measures, ticks_beats, beats_measure, beats_value):
    ''' function to create a DataFrame out of a dictionary:
        whose keys are all of the Measure Indexes of the current Midi,
        whose values are the Time Signature for that Measure, separated into 2 columns '''
        
    # List to store time signatures for each measure
    measure_time_signature_list = []

    # Initialize variables
    current_measure_index = 0
    current_ticks = 0
    
    # Iterate through each measure
    for measure_index in range(1, total_measures + 1):
        # Calculate the start and end ticks for the current measure
        measure_start_ticks = current_ticks
        measure_end_ticks = measure_start_ticks + (ticks_beats * beats_measure[current_measure_index][1] * (4 / beats_value[current_measure_index][1]))
        
        # Check if we need to move to the next beats_per_measure setting
        if (current_measure_index + 1 < len(beats_measure) and
            measure_start_ticks >= beats_measure[current_measure_index + 1][0]):
            current_measure_index += 1
        
        # Append the time signature for the current measure
        measure_time_signature_list.append({
            'Measure Index': measure_index,
            'Beats per Measure': beats_measure[current_measure_index][1],
            'Beats Value': beats_value[current_measure_index][1]
        })
        
        # Update the current ticks to the end of the current measure
        current_ticks = measure_end_ticks
    
    # Convert list of dicts to DataFrame
    measure_time_signature_df = pd.DataFrame(measure_time_signature_list)
    
    return measure_time_signature_df

