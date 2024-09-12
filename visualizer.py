import wave
import struct
import math
import cmath
import curses
import time
import argparse
import threading
import simpleaudio as sa

def read_wav_file(file_name):
    with wave.open(file_name, 'rb') as wf:
        num_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        frame_rate = wf.getframerate()
        num_frames = wf.getnframes()
        
        raw_data = wf.readframes(num_frames)
        total_samples = num_frames * num_channels
        fmt = f"<{total_samples}h"

        data = struct.unpack(fmt, raw_data)
        # only use one channel
        data = [data[i] for i in range(0, len(data), num_channels)]

    return data, frame_rate

def fft(x):
    N = len(x)
    if N <= 1:
        return x
    even = fft(x[0::2])
    odd = fft(x[1::2])
    T = [cmath.exp(-2j * math.pi * k / N) * odd[k] for k in range(N // 2)]
    return [even[k] + T[k] for k in range(N // 2)] + \
           [even[k] - T[k] for k in range(N // 2)]

def scale_spectrum(spectrum_complex, max_y):
    '''convert complex spectrum to real spectrum and scale it to fit the screen'''
    max_y = int((max_y // 2) *  0.8)
    spectrum = [abs(freq) for freq in spectrum_complex]
    max_spectrum = max(max(spectrum), 1)
    return [int(max_y * math.sqrt(freq) / math.sqrt(max_spectrum)) for freq in spectrum]


def draw_spectrum(stdscr, spectrum: list[int], max_y: int):
    global colors
    stdscr.clear()
    half_y = max_y // 2

    for i, freq in enumerate(spectrum):
        for j in range(freq):
            stdscr.addstr(half_y - j, i, "█", curses.color_pair(colors[j]))
            stdscr.addstr(half_y + j, i, "█", curses.color_pair(colors[j]))
    
def play_audio(file_name):
    wave_obj = sa.WaveObject.from_wave_file(file_name)
    play_obj = wave_obj.play()
    play_obj.wait_done()
    
def init_colors():
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, 1)
    curses.init_pair(2, curses.COLOR_WHITE, 1)
    curses.init_pair(3, curses.COLOR_GREEN, 1)
    curses.init_pair(4, curses.COLOR_YELLOW, 1)
    
def adjust_colors(max_y):
    global colors
    max_y = max_y // 2
    for i in range(max_y+1):
        if i / max_y <= 0.2:
            colors.append(1)
        elif i / max_y <= 0.4:
            colors.append(2)
        elif i / max_y <= 0.6:
            colors.append(3)
        else:
            colors.append(4)
            
def ema(alpha, prev, curr):
    new = []
    for i in range(len(curr)):
        if i >= len(prev):
            # dynamically adjust the size of terminal window may cause the length of prev and curr to be different
            new.append(int(curr[i])) 
        else:
            new.append(int((1 - alpha) * prev[i] + alpha * curr[i]))
    return new

def main(stdscr):
    init_colors()
    file_name = args.parse_args().file
    frame_size = 2048
    hop_size = 1024
    ema_alpha = 0.4 # the alpha value for EMA
    fps = 40

    data, frame_rate = read_wav_file(file_name)
    frame_duration = hop_size / frame_rate  # the duration of each `render frame``
    total_duration = len(data) / frame_rate  # the total duration of the audio
    
    if not args.parse_args().no_audio:
        audio_thread = threading.Thread(target=play_audio, args=(file_name,))
        audio_thread.start()

    play_start_time = time.time()
    
    previous_spectrum = None # the previous spectrum
    last_max_y, _ = stdscr.getmaxyx() # the last max y of the terminal window
    adjust_colors(last_max_y)
    
    cached_list = []
    ideal_frame_time = 1 / fps
    cached_size = max(ideal_frame_time // frame_duration, 1)
    
    for i in range(0, len(data) - frame_size, hop_size):
        start_time = time.time()
        
        # adjust the color when the terminal window size changes
        max_y, max_x = stdscr.getmaxyx()
        if max_y != last_max_y:
            adjust_colors(max_y)
            last_max_y = max_y
        
        spectrum = scale_spectrum(fft(data[i:i + frame_size])[:max_x], max_y)
        
        if len(cached_list) >= cached_size:
            # average the cached spectrum
            spectrum = [sum(x) // len(x) for x in zip(*cached_list)]
            cached_list = []
        
            # apply EMA
            if previous_spectrum is not None:
                spectrum = ema(ema_alpha, previous_spectrum, spectrum)
            # render the spectrum
            draw_spectrum(stdscr, spectrum, max_y)
            
            previous_spectrum = spectrum
        else:
            cached_list.append(spectrum)
        
        elapsed_time = time.time()
        
        _render_time = elapsed_time - start_time
        _frame_time = i / frame_rate
        _actual_frame_time = elapsed_time - play_start_time
        _delay = _actual_frame_time - _frame_time
        stdscr.addstr(max_y - 1, 0, f'({_actual_frame_time:.2f}s) {_frame_time:.2f} / {total_duration:.2f} s delay: {(_delay):.5f}s render: {_render_time:.5f}s frame: {frame_duration:.5f}s', curses.color_pair(0))
        stdscr.refresh()
        
        time.sleep(max(0, frame_duration - _render_time - _delay))
        
    audio_thread.join()

if __name__ == "__main__":
    args = argparse.ArgumentParser()
    # wav file path
    args.add_argument('-f', '--file', help='wav file path', type=str)
    # don't play audio
    args.add_argument('--no-audio', help='don\'t play audio', action='store_true')
    
    colors = []
    curses.wrapper(main)