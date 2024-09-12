# WAV Spectrum Visualizer

This is a simple tool(toy) that generates a spectrum visualization of a WAV file.

Blog post(Chinese): [Here](https://blog.soulter.top/posts/visualize-music.html)

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