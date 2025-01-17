#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from scipy.io import wavfile
import os
import numpy as np
from tqdm import tqdm
import json
import argparse
from datetime import datetime, timedelta


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Split a WAV file at points of silence.')
    # Required arguments
    parser.add_argument('input_file', type=str, help='Input audio file')
    parser.add_argument('output_dir', type=str, help='Output Directory')

    # Optional arguments with default values
    parser.add_argument('--min_silence_length', type=float, default=0.6,
                        help='Minimum length of silence (in seconds) to be used for splitting. Default is 0.6 seconds.')
    parser.add_argument('--silence_threshold', type=float,
                        default=1e-4, help='The energy level (between 0.0 and 1.0) below which the signal is regarded as silent.')
    parser.add_argument('--step_duration', type=float, default=0.03/10,
                        help='Step duration. Default is 0.003 seconds.')

    # Parse the arguments
    args = parser.parse_args()

    # Check to see if input_file exists
    if not os.path.exists(args.input_file):
        print("Error: The file '%s' does not exist." % args.input_file)
        sys.exit(1)

    # Check to see if output_dir exists
    if not os.path.exists(args.output_dir):
        print("Error: The directory '%s' does not exist." % args.output_dir)
        sys.exit(1)

    # Pass the arguments to the split_audio function
    split_audio(args.input_file, args.output_file, args.min_silence_length,
                args.silence_threshold, args.step_duration)


if __name__ == "__main__":
    main()

# Utility functions


def GetTime(video_seconds):

    if (video_seconds < 0):
        return 00

    else:
        sec = timedelta(seconds=float(video_seconds))
        d = datetime(1, 1, 1) + sec

        instant = str(d.hour).zfill(2) + ':' + str(d.minute).zfill(2) + \
            ':' + str(d.second).zfill(2) + str('.001')

        return instant


def GetTotalTime(video_seconds):

    sec = timedelta(seconds=float(video_seconds))
    d = datetime(1, 1, 1) + sec
    delta = str(d.hour) + ':' + str(d.minute) + ":" + str(d.second)

    return delta


def windows(signal, window_size, step_size):
    if type(window_size) is not int:
        raise AttributeError("Window size must be an integer.")
    if type(step_size) is not int:
        raise AttributeError("Step size must be an integer.")
    for i_start in range(0, len(signal), step_size):
        i_end = i_start + window_size
        if i_end >= len(signal):
            break
        yield signal[i_start:i_end]


def energy(samples):
    return np.sum(np.power(samples, 2.)) / float(len(samples))


def rising_edges(binary_signal):
    previous_value = 0
    index = 0
    for x in binary_signal:
        if x and not previous_value:
            yield index
        previous_value = x
        index += 1


def split_audio(input_file, output_file, min_silence_length, silence_threshold, step_duration):
    '''
    Last Acceptable Values

    min_silence_length = 0.3
    silence_threshold = 1e-3
    step_duration = 0.03/10

    '''

    # The minimum length of silence at which a split may occur [seconds]. Defaults to 3 seconds.
    min_silence_length = 0.6
    # The energy level (between 0.0 and 1.0) below which the signal is regarded as silent.
    silence_threshold = 1e-4
    # The amount of time to step forward in the input file after calculating energy. Smaller value = slower, but more accurate silence detection. Larger value = faster, but might miss some split opportunities. Defaults to (min-silence-length / 10.).
    step_duration = 0.03/10

    input_filename = input_file
    window_duration = min_silence_length
    if step_duration is None:
        step_duration = window_duration / 10.
    else:
        step_duration = step_duration

    output_filename_prefix = os.path.splitext(
        os.path.basename(input_filename))[0]
    dry_run = False

    print("Splitting {} where energy is below {}% for longer than {}s.".format(
        input_filename,
        silence_threshold * 100.,
        window_duration
    )
    )

    # Read and split the file

    sample_rate, samples = input_data = wavfile.read(
        filename=input_filename, mmap=True)

    max_amplitude = np.iinfo(samples.dtype).max
    print(max_amplitude)

    max_energy = energy([max_amplitude])
    print(max_energy)

    window_size = int(window_duration * sample_rate)
    step_size = int(step_duration * sample_rate)

    signal_windows = windows(
        signal=samples,
        window_size=window_size,
        step_size=step_size
    )

    window_energy = (energy(w) / max_energy for w in tqdm(
        signal_windows,
        total=int(len(samples) / float(step_size))
    ))

    window_silence = (e > silence_threshold for e in window_energy)

    cut_times = (r * step_duration for r in rising_edges(window_silence))

    # This is the step that takes long, since we force the generators to run.
    print("Finding silences...")
    cut_samples = [int(t * sample_rate) for t in cut_times]
    cut_samples.append(-1)

    cut_ranges = [(i, cut_samples[i], cut_samples[i+1])
                  for i in range(len(cut_samples) - 1)]

    video_sub = {str(i): [str(GetTime(((cut_samples[i])/sample_rate))),
                          str(GetTime(((cut_samples[i+1])/sample_rate)))]
                 for i in range(len(cut_samples) - 1)}

    for i, start, stop in tqdm(cut_ranges):
        output_file_path = "{}_{:03d}.wav".format(
            os.path.join(output_dir, output_filename_prefix),
            i
        )
        if not dry_run:
            print("Writing file {}".format(output_file_path))
            wavfile.write(
                filename=output_file_path,
                rate=sample_rate,
                data=samples[start:stop]
            )
        else:
            print("Not writing file {}".format(output_file_path))

    with open(output_dir+'\\'+output_filename_prefix+'.json', 'w') as output:
        json.dump(video_sub, output)
