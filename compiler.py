#!/usr/bin/env python3


'''
Copyright © 2023 fordel-0 <00.frdl@gmail.com>
This work is free. You can redistribute it and/or modify it under the
terms of the Do What The Fuck You Want To Public License, Version 2,
as published by Sam Hocevar. See the COPYING file for more details.
'''


import argparse
import wave


note_list = "cCdDefFgGaAb"


class Compiler:
	def __init__(self, path):
		self.mspb = 500
		self.a1 = 55
		self.time = 1
		self.beeps = []
		self.mode = "notes"
		with open(path, "rt") as file:
			self.compile(file.read())

	def compile(self, source):
		for line in source.split("\n"):
			line = crop_line(line)

			if line == "" or line[0] != "!":
				self.beeps += self.compile_line(line)
			else:
				self.parse_bang(line)
		return self.beeps

	def parse_bang(self, line):
		line = line.replace(" ", "")
		s = line[1:].split("=")
		key, value = s
		match key:
			case "mode":
				if value not in ["notes", "tabs"]:
					raise Exception("Unknown mode")
				self.mode = value
			case "bpm":
				self.mspb = bpm_to_mspb(int(value))
			case "a4":
				self.a4 = a4_to_a1(int(value))
			case "time":
				self.time = eval(value, {})
			case _:
				raise Exception(f"Unknown param {key}")

	def compile_line(self, line):
		tokens = tokenize(line)
		beeps = []
		note_len = self.mspb / self.time
		prev_note = 0
		for token in tokens:
			if token[0] in note_list:
				beeps.append([note_to_freq(token, self.a1), note_len])
				prev_note = beeps[-1][0]
			elif token == "-":
				if beeps[-1][0] != 0:
					beeps[-1][1] += note_len
				else:
					beeps.append([prev_note, note_len])
			elif token == "_":
				beeps.append([0, note_len])
			else:
				raise Exception(f"Unknown token {token}")
		return beeps


def beeps_to_script(beeps):
	formated_beeps = [f"-f {beep[0]} -l {beep[1]}" for beep in beeps]
	return "beep " + " -n ".join(formated_beeps)


def beeps_to_frames(beeps, framerate=44100):
	frames = b""
	for beep in beeps:
		frames += generate_square_beep(beep, framerate)
	return frames


def generate_square_beep(beep, framerate):
	length = mss_to_frames(beep[1], framerate)
	if beep[0] == 0:
		return b"\x60" * length
	frames = b""
	premult = framerate / beep[0]
	if int(premult) != 0:
		while length // (2 * premult) > 0:
			frames += b"\x00" * int(premult) + b"\xC0" * int(premult)
			length -= 2 * int(premult)
	for frame in range(length):
		frames += generate_square_frame(frame, 2 * premult)
	return frames


def generate_square_frame(frame, premult):
	if int(frame * premult) % 2:
		return b"\x00"
	else:
		return b"\xC0"


def mss_to_frames(mss, framerate):
	return int(framerate * mss / 1000)


def tokenize(line):
	tokens = []
	i = 0
	while i < len(line):
		if line[i] in note_list:
			tokens.append(line[i:i + 2])
			i += 2
		elif line[i] == "-" or line[i] == "_":
			tokens.append(line[i])
			i += 1
		elif line[i] == " ":
			i += 1
		else:
			raise Exception(f"Unknown symbol {line[i]}")
	return tokens


def bpm_to_mspb(bpm):
	return round(60000 / bpm, 3)


def a4_to_a1(a4):
	return a4 / 8


def note_to_freq(full_note, a1):
	note, octave = full_note
	octave = int(octave) - 1
	note_index = octave + note_list.index(note) / 12
	return round(a1 * (2 ** note_index), 3)


def crop_line(line):
	sharp_pos = line.find("#")
	if sharp_pos == -1:
		return line
	return line[:sharp_pos]


if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog="fordel's Speaker Music Compiler",
									 description="Compiles speaker music")
	parser.add_argument('filename')
	args = parser.parse_args()

	compiler = Compiler(args.filename)
	frames = beeps_to_frames(compiler.beeps)
	with wave.open(f"../storage/music/{args.filename}.wav", "wb") as file:
		file.setparams((1, 1, 44100, 0, "NONE", "not compressed"))
		file.writeframes(frames)
