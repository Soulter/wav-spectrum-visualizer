# WAV Spectrum Visualizer

This is a simple tool(toy) that generates a spectrum visualization of a WAV file. Inspired by `ncmpcpp`'s spectrum visualizer.

Blog post(Chinese): [Here](https://blog.soulter.top/posts/visualize-music.html)


## Demo

https://github.com/user-attachments/assets/7ba1eb42-50de-40d0-8e30-187a6bc229a5

## Usage

Install the required dependencies:

```bash
pip3 install -r requirements.txt
```

The following command will **play the WAV audio** and display the spectrum visualization:
```bash
python3 visualizer.py -f <path_to_wav_file>
```

Just add the `--no-audio` flag if you don't want to play the audio, :

```bash
python3 visualizer.py -f <path_to_wav_file> --no-audio
```
