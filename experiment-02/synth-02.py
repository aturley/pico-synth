import math

def gen_midi_table():
    midi_table = []
    n0 = 8.175
    for i in range(0, 128):
        midi_table.append(n0 * math.pow(2, i / 12))

    return midi_table

def gen_cycle(bits, n_samples):
    volume_reduction_factor = 32
    sample_size_in_bytes = bits // 8
    bias = pow(2, bits) // 2 // volume_reduction_factor
    b_samples = bytearray(n_samples * sample_size_in_bytes)

    return [(bias + (int((bias - 1) * math.sin(2 * math.pi * x / n_samples)))) for x in range(0, n_samples)]

def gen_sample(freq, sr, bits, cycle, sample):
    sample_size_in_bytes = bits // 8
    stride = freq * len(cycle) / sr

    if bits == 16:
        fmt = "<h"
    else:
        fmt = "<l"

    pos = 0
    
    for i in range(0, len(cycle)):
        s = cycle[int(pos) % len(cycle)]
        struct.pack_into(fmt, sample, i * sample_size_in_bytes, s)
        pos = pos + stride

class CycleIterator:
    def __init__(self, freq, sr, bits, cycle):
        self.cycle = cycle
        self.pos = 0
        self.sample_size_in_bytes = bits // 8
        self.stride = freq * len(cycle) / sr
        if bits == 16:
            self.fmt = "<h"
        else:
            self.fmt = "<l"
        
    def make_cycle_iterator(self, n_samples):
        for _ in range(0, n_samples):
            s = self.cycle[int(self.pos)]
            for i in range(0, self.sample_size_in_bytes):
                yield (s >> (i * 8)) & 0xFF
            
            self.pos = self.pos + self.stride

            if self.pos > len(self.cycle):
                self.pos = self.pos - len(self.cycle)

midi_table = gen_midi_table()

# Simple MIDI Monitor
#
# @diyelectromusic
# https://diyelectromusic.wordpress.com/
#
#      MIT License
#      
#      Copyright (c) 2020 diyelectromusic (Kevin)
#      
#      Permission is hereby granted, free of charge, to any person obtaining a copy of
#      this software and associated documentation files (the "Software"), to deal in
#      the Software without restriction, including without limitation the rights to
#      use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
#      the Software, and to permit persons to whom the Software is furnished to do so,
#      subject to the following conditions:
#      
#      The above copyright notice and this permission notice shall be included in all
#      copies or substantial portions of the Software.
#      
#      THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#      IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
#      FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
#      COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHERIN
#      AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
#      WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
import machine
import utime
import ustruct

pin = machine.Pin(25, machine.Pin.OUT)
uart = machine.UART(1,31250)

# Basic MIDI handling commands
def doMidiNoteOn(note,vel):
    global note_iterator
    pin.value(1)
    print("Note On \t", note, "\t", vel)
    freq = midi_table[note]
    print("freq\t", freq)

    note_iterator = CycleIterator(freq, 22050, 16, cycle)

def doMidiNoteOff(note,vel):
    global note_iterator
    pin.value(0)
    print("Note Off\t", note, "\t", vel)

    note_iterator = None

# Implement a simple MIDI decoder.
#
# MIDI supports the idea of Running Status.
#
# If the command is the same as the previous one, 
# then the status (command) byte doesn't need to be sent again.
#
# The basis for handling this can be found here:
#  http://midi.teragonaudio.com/tech/midispec/run.htm
# Namely:
#   Buffer is cleared (ie, set to 0) at power up.
#   Buffer stores the status when a Voice Category Status (ie, 0x80 to 0xEF) is received.
#   Buffer is cleared when a System Common Category Status (ie, 0xF0 to 0xF7) is received.
#   Nothing is done to the buffer when a RealTime Category message is received.
#   Any data bytes are ignored when the buffer is 0.
#
MIDICH = 1
MIDIRunningStatus = 0
MIDINote = 0
MIDILevel = 0
def doMidi(mb):
    global MIDIRunningStatus
    global MIDINote
    global MIDILevel
    if ((mb >= 0x80) and (mb <= 0xEF)):
        # MIDI Voice Category Message.
        # Action: Start handling Running Status
        MIDIRunningStatus = mb
        MIDINote = 0
        MIDILevel = 0
    elif ((mb >= 0xF0) and (mb <= 0xF7)):
        # MIDI System Common Category Message.
        # Action: Reset Running Status.
        MIDIRunningStatus = 0
    elif ((mb >= 0xF8) and (mb <= 0xFF)):
        # System Real-Time Message.
        # Action: Ignore these.
        pass
    else:
        # MIDI Data
        if (MIDIRunningStatus == 0):
            # No record of what state we're in, so can go no further
            return
        if (MIDIRunningStatus == (0x80|(MIDICH-1))):
            # Note OFF Received
            if (MIDINote == 0):
                # Store the note number
                MIDINote = mb
            else:
                # Already have the note, so store the level
                MIDILevel = mb
                doMidiNoteOff (MIDINote, MIDILevel)
                MIDINote = 0
                MIDILevel = 0
        elif (MIDIRunningStatus == (0x90|(MIDICH-1))):
            # Note ON Received
            if (MIDINote == 0):
                # Store the note number
                MIDINote = mb
            else:
                # Already have the note, so store the level
                MIDILevel = mb
                if (MIDILevel == 0):
                    doMidiNoteOff (MIDINote, MIDILevel)
                else:
                    doMidiNoteOn (MIDINote, MIDILevel)
                MIDINote = 0
                MIDILevel = 0
        else:
            # This is a MIDI command we aren't handling right now
            pass

# while True:
#     if (uart.any()):
#         doMidi(uart.read(1)[0])

# The MIT License (MIT)
# Copyright (c) 2022 Mike Teachman
# https://opensource.org/licenses/MIT

# Purpose:  Play a pure audio tone out of a speaker or headphones
#
# - write audio samples containing a pure tone to an I2S amplifier or DAC module
# - tone will play continuously in a loop until
#   a keyboard interrupt is detected or the board is reset
#
# Blocking version
# - the write() method blocks until the entire sample buffer is written to I2S

import os
import math
import struct
from machine import I2S
from machine import Pin

def make_tone(rate, bits, frequency):
    # create a buffer containing the pure tone samples
    samples_per_cycle = rate // frequency
    sample_size_in_bytes = bits // 8
    samples = bytearray(samples_per_cycle * sample_size_in_bytes)
    volume_reduction_factor = 32
    range = pow(2, bits) // 2 // volume_reduction_factor
    
    if bits == 16:
        format = "<h"
    else:  # assume 32 bits
        format = "<l"
    
    for i in range(samples_per_cycle):
        sample = range + int((range - 1) * math.sin(2 * math.pi * i / samples_per_cycle))
        struct.pack_into(format, samples, i * sample_size_in_bytes, sample)
        
    return samples

if os.uname().machine.count("PYBv1"):

    # ======= I2S CONFIGURATION =======
    SCK_PIN = "Y6"
    WS_PIN = "Y5"
    SD_PIN = "Y8"
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 2000
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("PYBD"):
    import pyb

    pyb.Pin("EN_3V3").on()  # provide 3.3V on 3V3 output pin

    # ======= I2S CONFIGURATION =======
    SCK_PIN = "Y6"
    WS_PIN = "Y5"
    SD_PIN = "Y8"
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 2000
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("ESP32"):

    # ======= I2S CONFIGURATION =======
    SCK_PIN = 32
    WS_PIN = 25
    SD_PIN = 33
    I2S_ID = 0
    BUFFER_LENGTH_IN_BYTES = 2000
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("Raspberry"):

    # ======= I2S CONFIGURATION =======
    SCK_PIN = 16
    WS_PIN = 17
    SD_PIN = 18
    I2S_ID = 0
    BUFFER_LENGTH_IN_BYTES = 2000
    # ======= I2S CONFIGURATION =======

elif os.uname().machine.count("MIMXRT"):

    # ======= I2S CONFIGURATION =======
    SCK_PIN = 4
    WS_PIN = 3
    SD_PIN = 2
    I2S_ID = 2
    BUFFER_LENGTH_IN_BYTES = 2000
    # ======= I2S CONFIGURATION =======

else:
    print("Warning: program not tested with this board")

# ======= AUDIO CONFIGURATION =======
TONE_FREQUENCY_IN_HZ = 440
SAMPLE_SIZE_IN_BITS = 16
FORMAT = I2S.MONO  # only MONO supported in this example
SAMPLE_RATE_IN_HZ = 22_050
# ======= AUDIO CONFIGURATION =======

audio_out = I2S(
    I2S_ID,
    sck=Pin(SCK_PIN),
    ws=Pin(WS_PIN),
    sd=Pin(SD_PIN),
    mode=I2S.TX,
    bits=SAMPLE_SIZE_IN_BITS,
    format=FORMAT,
    rate=SAMPLE_RATE_IN_HZ,
    ibuf=BUFFER_LENGTH_IN_BYTES,
)

# samples440 = make_tone(SAMPLE_RATE_IN_HZ, SAMPLE_SIZE_IN_BITS, TONE_FREQUENCY_IN_HZ)
# samples379 = make_tone(SAMPLE_RATE_IN_HZ, SAMPLE_SIZE_IN_BITS, 379)

cycle = gen_cycle(16, 2000)

# samples440 = bytearray(BUFFER_LENGTH_IN_BYTES * (SAMPLE_SIZE_IN_BITS) // 8)
# samples379 = bytearray(BUFFER_LENGTH_IN_BYTES * (SAMPLE_SIZE_IN_BITS) // 8)

# gen_sample(440, 22050, 16, cycle, samples440)
# gen_sample(379, 22050, 16, cycle, samples379)

ci440 = CycleIterator(440, 22050, 16, cycle)
samples440 = bytearray(ci440.make_cycle_iterator(2000))

ci379 = CycleIterator(379, 22050, 16, cycle)
samples379 = bytearray(ci379.make_cycle_iterator(2000))

samples_silence = bytearray(4000)

note_iterator = None

some_samples = [samples440, samples379]
samples_idx = 0

samples = some_samples[samples_idx]

next_sample = samples_silence

# continuously write tone sample buffer to an I2S DAC
# print("==========  START PLAYBACK ==========")
# try:
#     while True:
#         num_written = audio_out.write(samples)

# except (KeyboardInterrupt, Exception) as e:
#     print("caught exception {} {}".format(type(e).__name__, e))

# # cleanup
# audio_out.deinit()
# print("Done")

def write_samples(arg):
    # audio_out.write(samples)
    global next_sample
    if next_sample:
        audio_out.write(next_sample)
    else:
        audio_out.write(samples_silence)
    next_sample = None

def main():
    global next_sample
    try:
        audio_out.irq(write_samples)
        audio_out.write(samples_silence)
    
        while True:
            if next_sample == None:
                if note_iterator:
                    next_sample = bytearray(note_iterator.make_cycle_iterator(2000))
                else:
                    next_sample = samples_silence
            if (uart.any()):  
                v = uart.read(1)[0]
                print("got", v, "0x" + hex(v))
                doMidi(v)


    except (KeyboardInterrupt, Exception) as e:
        print("caught exception {} {}".format(type(e).__name__, e))

    audio_out.deinit()
    print("Done")

main()
