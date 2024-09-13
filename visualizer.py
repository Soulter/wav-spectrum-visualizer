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
        frame_rate = wf.getframerate()
        num_frames = wf.getnframes()
        
        raw_data = wf.readframes(num_frames)
        total_samples = num_frames * num_channels
        fmt = f"<{total_samples}h"

        data = struct.unpack(fmt, raw_data)
        parsed_data = []
        for i in range(num_channels):
            parsed_data.append(data[i::num_channels])

    return parsed_data, frame_rate

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
    spectrum = [abs(freq) for freq in spectrum_complex]
    max_spectrum = max(max(spectrum), 1)
    return [int(max_y * math.sqrt(freq) / math.sqrt(max_spectrum)) for freq in spectrum]

def draw_spectrum(stdscr, spectrum: list[list[int]], max_y: int):
    global colors
    stdscr.clear()
    half_y = max_y // 2

    for i, freq in enumerate(spectrum[0]):
        full_1 = min(freq // len(blocks), len(colors))
        full_2 = min(spectrum[1][i] // len(blocks), len(colors))
        left_1 = freq % len(blocks)
        left_2 = spectrum[1][i] % len(blocks)
        
        # draw the full blocks
        for j in range(full_1):
            stdscr.addstr(half_y - j, i, blocks[-1], curses.color_pair(colors[j]))
            if len(spectrum) == 1:
                # if the audio file only has one channel, draw the same spectrum for the other channel
                stdscr.addstr(half_y + j, i, blocks[-1], curses.color_pair(colors[j]))
                continue
        for j in range(full_2):
            stdscr.addstr(half_y + j, i, blocks[-1], curses.color_pair(colors[j]))
        
        # draw the left blocks
        if left_1 > 0:
            stdscr.addstr(half_y - full_1, i, blocks[left_1], curses.color_pair(colors[full_1-1]))
            if len(spectrum) == 1:
                stdscr.addstr(half_y + full_1, i, blocks[left_1], curses.color_pair(colors_reverse[full_1-1]))
        if left_2 > 0:
            stdscr.addstr(half_y + full_2, i, blocks[left_2], curses.color_pair(colors_reverse[full_2-1]))

def play_audio(file_name):
    wave_obj = sa.WaveObject.from_wave_file(file_name)
    play_obj = wave_obj.play()
    play_obj.wait_done()
    
def init_colors():
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    
    curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    
def adjust_colors(max_y):
    global colors, colors_reverse
    max_y = int (max_y / 2 * 0.8)
    colors = []
    colors_reverse = []
    for i in range(max_y+1):
        if i / max_y <= 0.25:
            colors.append(1)
            colors_reverse.append(5)
        elif i / max_y <= 0.45:
            colors.append(2)
            colors_reverse.append(6)
        elif i / max_y <= 0.65:
            colors.append(3)
            colors_reverse.append(7)
        else:
            colors.append(4)
            colors_reverse.append(8)
            
def ema(alpha_down: float, alpha_up: float, prev: list, curr: list):
    '''Exponential Moving Average'''
    new = []
    for i in range(len(curr)):
        if i >= len(prev):
            # dynamically adjust the size of terminal window may cause the length of prev and curr to be different
            new.append(int(curr[i])) 
        else:
            if prev[i] > curr[i]:
                new.append(int(alpha_down * prev[i] + (1 - alpha_down) * curr[i]))
            else:
                new.append(int(alpha_up * prev[i] + (1 - alpha_up) * curr[i]))
    return new

def main(stdscr):
    init_colors()
    file_name = args.parse_args().file
    frame_size = 2048
    hop_size = 1600
    
    # The EMA alpha. Means the weight of the **previous** spectrum.
    ema_alpha_down = 0.93 # when previous value > current value
    ema_alpha_up = 0.2 # when previous value <= current value

    data, frame_rate = read_wav_file(file_name)
    frame_duration = hop_size / frame_rate  # the duration of each `render frame``
    total_duration = len(data[0]) / frame_rate  # the total duration of the audio
    
    if not args.parse_args().no_audio:
        audio_thread = threading.Thread(target=play_audio, args=(file_name,))
        audio_thread.start()

    play_start_time = time.time()
    
    previous_spectrum = None # the previous spectrum
    last_max_y, _ = stdscr.getmaxyx() # the last max y of the terminal window
    last_scale_max_val = int((last_max_y * len(blocks) // 2) * 0.8)
    adjust_colors(last_max_y)
    
    for i in range(0, len(data[0]) - frame_size, hop_size):
        start_time = time.time()
        
        # adjust the color when the terminal window size changes
        max_y, max_x = stdscr.getmaxyx()
        if max_y != last_max_y:
            adjust_colors(max_y)
            last_max_y = max_y
            last_scale_max_val = int((max_y * len(blocks) // 2) * 0.8)
        
        spectrum = [] # len(fft_data) == channel num
        for channel_idx in range(len(data)):
            spectrum.append(scale_spectrum(fft(data[channel_idx][i:i + frame_size])[:max_x], last_scale_max_val))

        # apply EMA
        if previous_spectrum is not None:
            for channel_idx in range(len(spectrum)):
                spectrum[channel_idx] = ema(ema_alpha_down, 
                                            ema_alpha_up, 
                                            previous_spectrum[channel_idx], 
                                            spectrum[channel_idx])
        # render the spectrum
        draw_spectrum(stdscr, spectrum, max_y)
        
        previous_spectrum = spectrum
        
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
    blocks = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    
    args = argparse.ArgumentParser()
    # wav file path
    args.add_argument('-f', '--file', help='wav file path', type=str)
    # don't play audio
    args.add_argument('--no-audio', help='don\'t play audio', action='store_true')
    
    colors = []
    colors_reverse = []
    curses.wrapper(main)