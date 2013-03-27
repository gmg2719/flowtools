#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# flowdiff.py - shows differences between Flow objects
#
# Copyright (c) 2013 András Veres-Szentkirályi
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from flow import Flow
from itertools import izip, islice, imap, chain
from operator import attrgetter
from binascii import hexlify
from ui import COLORS, horizontal_separator, width

def diff_flows(flows, skip_offset=None, max_entries=None):
	if skip_offset is not None:
		flows = (f.filter_by_offset(skip_offset) for f in flows)
	for entry_no, entries in enumerate(izip(*flows)):
		if max_entries is not None and entry_no == max_entries:
			break

		lengths = set(len(e.data) for e in entries)
		print '[i] E{entry_no} // {dirs} // Offset: {offsets} // Length: {lens}'.format(
				entry_no=entry_no,
				offsets=sorted(set(e.offset for e in entries)),
				dirs='/'.join(sorted(set(
					COLORS[Flow.DIRECTIONS.index(e.direction)](e.direction)
					for e in entries))),
				lens=sorted(lengths))

		min_len = min(lengths)
		first_data = entries[0].data
		common_bytes = [n for n in xrange(min_len) if all(e.data[n] == first_data[n] for e in entries[1:])]
		
		if len(lengths) > 1:
			look_for_length_byte(entries)
			for match_len in xrange(min_len - 1, 0, -1):
				fd_match = first_data[-match_len:]
				if all(e.data[-match_len:] == fd_match for e in entries[1:]):
					print '[i] Common postfix: {0}'.format(':'.join(
						COLORS[len(Flow.DIRECTIONS)](hexlify(c)) for c in fd_match))
					break

		all_same = (len(set(e.data for e in entries)) == 1)
		if all_same:
			entries = (entries[0],)
		else:
			look_for_fix_diff(entries)

		for i, entry in enumerate(entries):
			print ''
			hexdump, asciidump = ([(empty if (n in common_bytes and i) else COLORS[
				next(bi for bi, be in enumerate(entries) if len(be.data) >= n + 1 and
					be.data[n] == c)](conv(c)))
				for n, c in enumerate(entry.data)] for empty, conv in
				(('..', hexlify), ('.', asciify)))
			bytes_per_line = (width - (1 + 8 + 2 + 2)) / 17 * 4
			for offset in xrange(0, len(entry.data), bytes_per_line):
				print '{offset:08x}  {hex}  {ascii}'.format(offset=offset,
					hex='  '.join(' '.join(padspace(hexdump[do:do + 4], 4))
						for do in xrange(offset, offset + bytes_per_line, 4)),
					ascii=''.join(asciidump[offset:offset + bytes_per_line]))
	
		if all_same:
			print '(all entries are the same)'

		horizontal_separator()

def padspace(data, length):
	return data if len(data) >= length else chain(data, ['  '] * (length - len(data)))

def asciify(bytestr):
	return bytestr if 0x20 <= ord(bytestr) <= 0x7e else '.'

def look_for_length_byte(entries):
	for i, pos_bytes in enumerate(izip(*(e.data for e in entries))):
		diffs = set(ord(b) - len(e.data) for e, b in izip(entries, pos_bytes))
		if len(diffs) == 1:
			diff = abs(next(iter(diffs)))
			print '[i] Possible length byte at offset 0x{0:02x}, diff = {1}'.format(i, diff)

def look_for_fix_diff(entries):
	pos_bytes_range = range(1, len(entries))
	for i, pos_bytes_1 in enumerate(izip(*imap(attrgetter('data'), entries))):
		if len(set(pos_bytes_1)) == 1:
			continue
		for j, pos_bytes_2 in islice(enumerate(izip(*imap(attrgetter('data'), entries))), i):
			diff = ord(pos_bytes_1[0]) - ord(pos_bytes_2[0])
			for k in pos_bytes_range:
				if ord(pos_bytes_1[k]) - ord(pos_bytes_2[k]) != diff:
					break
			else:
				di, dj = ('0x{0:02x} [{1}]'.format(pos, ' '.join(c(hexlify(v)) for c, v in izip(COLORS, values)))
						for pos, values in ((i, pos_bytes_1), (j, pos_bytes_2)))
				fmt = ('[i] difference between bytes {0} and {1} is always {2}'
						if diff else '[i] bytes {0} and {1} always match')
				print fmt.format(di, dj, abs(diff))

def main():
	from sys import argv
	if '-h' in argv:
		return print_usage()
	n = 1
	filenames = []
	skip_offset = {}
	max_entries = None
	try:
		while n < len(argv):
			arg = argv[n]
			if arg == '-m':
				n += 1
				max_entries = int(argv[n])
			elif arg == '-s':
				n += 1
				skip_offset[Flow.SENT] = int(argv[n])
			elif arg == '-r':
				n += 1
				skip_offset[Flow.RECEIVED] = int(argv[n])
			else:
				filenames.append(arg)
			n += 1
		if not filenames:
			raise ValueError('No files were given that day')
	except (ValueError, IndexError):
		print_usage()
		raise SystemExit(1)
	else:
		flows = [Flow(fn) for fn in filenames]
		diff_flows(flows, skip_offset=skip_offset, max_entries=max_entries)
		print 'Input files:'
		for n, fn in enumerate(filenames):
			print ' - ' + COLORS[n](fn)

def print_usage():
	from sys import argv, stderr
	print >> stderr, "Usage: {0} [-m max_entries] [-s skip_sent_bytes] [-r skip_recvd_bytes] <filename> ...".format(argv[0])

if __name__ == '__main__':
	main()
