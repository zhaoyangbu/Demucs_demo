import io
from pathlib import Path
import select
import subprocess as sp
import sys
from typing import Dict, Tuple, Optional, IO
from pydub import AudioSegment

mp3 = True
mp3_rate = 320
model = "mdx_extra"
extensions = ["mp3", "wav", "ogg", "flac", "m4a"]
in_path = 'input'
temp_path = 'temp'
temp_path_hat = 'temp/mdx_extra'
out_path = 'output'

def find_files(in_path):
    out = []
    for file in Path(in_path).iterdir():
        if file.suffix.lower().lstrip(".") in extensions:
            out.append(file)
    return out

def find_dir(in_path):
    out = []
    out_name = []
    for dir in Path(in_path).iterdir():
        dir_name = str(dir)
        dir_name = dir_name.split('/')[-1]
        if dir_name ==".DS_Store":
            continue
        else:
            out.append(dir)
            out_name.append(dir_name)
    return out, out_name

def copy_process_streams(process: sp.Popen):
    def raw(stream: Optional[IO[bytes]]) -> IO[bytes]:
        assert stream is not None
        if isinstance(stream, io.BufferedIOBase):
            stream = stream.raw
        return stream

    p_stdout, p_stderr = raw(process.stdout), raw(process.stderr)
    stream_by_fd: Dict[int, Tuple[IO[bytes], io.StringIO, IO[str]]] = {
        p_stdout.fileno(): (p_stdout, sys.stdout),
        p_stderr.fileno(): (p_stderr, sys.stderr),
    }
    fds = list(stream_by_fd.keys())

    while fds:
        # `select` syscall will wait until one of the file descriptors has content.
        ready, _, _ = select.select(fds, [], [])
        for fd in ready:
            p_stream, std = stream_by_fd[fd]
            raw_buf = p_stream.read(2 ** 16)
            if not raw_buf:
                fds.remove(fd)
                continue
            buf = raw_buf.decode()
            std.write(buf)
            std.flush()

def separate(inp=None, outp=None):
    inp = inp or in_path
    outp = outp or temp_path
    cmd = ["python3", "-m", "demucs.separate", "-o", str(outp), "-n", model]
    if mp3:
        cmd += ["--mp3", f"--mp3-bitrate={mp3_rate}"]
    files = [str(f) for f in find_files(inp)]
    if not files:
        print(f"No valid audio files in {in_path}")
        return
    print("Going to separate the files:")
    print('\n'.join(files))
    print("With command: ", " ".join(cmd))
    p = sp.Popen(cmd + files, stdout=sp.PIPE, stderr=sp.PIPE)
    copy_process_streams(p)
    p.wait()
    if p.returncode != 0:
        print("Command failed, something went wrong.")

def gen_accomp(path=None):
    path = path or temp_path_hat
    paths, _ = [s for s in find_dir(path)]
    for i in range(len(paths)):
        drum_path = f"{paths[i]}/drums.mp3"
        bass_path = f"{paths[i]}/bass.mp3"
        other_path = f"{paths[i]}/other.mp3"
        sound1 = AudioSegment.from_mp3(drum_path)
        sound2 = AudioSegment.from_mp3(bass_path)
        sound3 = AudioSegment.from_mp3(other_path)
        output_hat = sound1.overlay(sound2)
        output = sound3.overlay(output_hat)
        output.export(f"{paths[i]}/accompaniment.mp3", format="mp3", parameters=["-ac", "2"])



def m4a_converter(inp=None, outp=None):
    inp = inp or temp_path_hat
    outp = outp or out_path
    parts = ['vocals', 'accompaniment']
    paths, song_names = [s for s in find_dir(inp)]
    for i in range(len(song_names)):
        for part in parts:
            cmd = ["ffmpeg", "-i", f"{paths[i]}/{part}.mp3", "-c:v", "copy", f"{out_path}/{song_names[i]}_{part}.m4a"]
            print("Going to convert files in:")
            print(paths)
            print("with", cmd)
            p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
            p.wait()
            if p.returncode != 0:
                print("Command failed, something went wrong.")
    
def clean_cache(path=None):
    path = path or temp_path_hat
    cmd = ["rm", "-rf", f"{path}"]
    p = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE)

if __name__ == "__main__":
    #separate()
    gen_accomp()
    m4a_converter()
    #clean_cache()
