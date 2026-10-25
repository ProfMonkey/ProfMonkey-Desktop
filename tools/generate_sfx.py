"""Original tiny synthesized sound effects; WAVs only, offline."""
from pathlib import Path
import wave
import math
import struct
import random

OUT = Path(__file__).resolve().parents[1]/'assets/audio'
OUT.mkdir(parents=True,exist_ok=True)
RATE = 22050


def synth(name, duration, start_hz, end_hz, style='tone'):
    rng = random.Random(len(name))
    n = int(duration*RATE)
    values=[]
    phase=0.0
    for i in range(n):
        t=i/n
        freq=start_hz*(1-t)+end_hz*t
        phase += math.tau*freq/RATE
        envelope=(1-t)**1.8*min(1., t*40)
        wavelet=math.sin(phase)
        if style=='square':
            wavelet = math.tanh(2.3*wavelet)
        elif style=='noise':
            wavelet = .55*wavelet+.45*rng.uniform(-1,1)
        values.append(max(-32000,min(32000,round(wavelet*envelope*9000))))
    with wave.open(str(OUT/f'{name}.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
        w.writeframes(struct.pack('<'+('h'*len(values)),*values))


def main():
    synth('click',.09,700,450)
    synth('banana',.22,520,880)
    synth('slip',.27,900,190,'square')
    synth('fall',.34,280,75,'noise')
    synth('win',.30,520,1050)

if __name__=='__main__':main()
