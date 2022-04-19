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
    pin.value(1)
    print("Note On \t", note, "\t", vel)
    global samples
    global samples_idx
    samples_idx = (samples_idx + 1) % len(some_samples)
    samples = some_samples[samples_idx]


def doMidiNoteOff(note,vel):
    pin.value(0)
    print("Note Off\t", note, "\t", vel)

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

samples440 = make_tone(SAMPLE_RATE_IN_HZ, SAMPLE_SIZE_IN_BITS, TONE_FREQUENCY_IN_HZ)
samples379 = make_tone(SAMPLE_RATE_IN_HZ, SAMPLE_SIZE_IN_BITS, 379)

some_samples = [samples440, samples379]
samples_idx = 0

samples = some_samples[samples_idx]

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
    audio_out.write(samples)

try:
    audio_out.irq(write_samples)
    audio_out.write(samples)
    
    while True:
        if (uart.any()):  
            v = uart.read(1)[0]
            print("got", v, "0x" + hex(v))
            doMidi(v)


except (KeyboardInterrupt, Exception) as e:
    print("caught exception {} {}".format(type(e).__name__, e))

audio_out.deinit()
print("Done")
