#!/usr/bin/env python3

"""
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

import io
import os.path as fs
import sys
import zlib


print("""split-zimage.py script by arzamas-16 (https://github.com/arzam16)
                insipred by DeckerSU: https://github.com/DeckerSU""")
if len(sys.argv) != 2 or sys.argv[1] == "-h":
    print("""
Usage: split-zimage.py boot.img-zImage

This script splits extracted zImage into 2 or 3 parts.
After splitting it's possible to obtain the Linux kernel
binary by decompressing the '2_kernel_image.gz' file.

Intended workflow:
1. Unpack the boot.img with AIK-Linux
2. Feed boot.img-zImage to this script
3. Decompress 2_kernel_image.gz
4. Do further modifications

Limitations:
* Supports GZIP compression only""")
    exit()

# Small sanity check
if len(sys.argv) != 2 or not fs.exists(sys.argv[1]):
    exit("Input file is not specified or doesn't exist")


"""
Locates sublist in list. Allows to search from the end. Limits max offset of
search to half of the list to save time. Returns -1 if nothing was found.
"""


def where_is(what, _in, reverse=False):
    limit = len(_in) // 2

    offsets = None
    if not reverse:
        offsets = range(min(len(_in), limit))
    else:
        offsets = range(
            len(_in) - len(what),
            max(0, len(_in) - limit),
            -1
        )

    for i in offsets:
        if _in[i] == what[0] and _in[i:i+len(what)] == what:
            return i
    return -1


"""
# Read the entire zImage into memory. Usually zImage consists of 3 parts:
# 1. Header. This is a boot executable which unpacks and starts the kernel.
# 2. Compressed kernel image. It's a valid .gz archive.
# 3. Footer. May contain additional information such as DTB.
# zImage = [Header + kernel.gz + Footer]
"""
zimage = None
with open(sys.argv[1], "rb") as f:
    zimage = io.BytesIO(f.read()).getbuffer()


"""
Header doesn't have its own distinctive magic bytes at the start or end.
To separate it from other parts of zImage, find start offset of compressed
kernel image. Standardized GZ header is 1F8B but UBoot also checks for 0x08.
"""
GZ_HDR = bytearray([0x1F, 0x8B, 0x08])
gz_off_start = where_is(GZ_HDR, zimage)
if gz_off_start == -1:
    exit("Couldn't find gzip magic in file")


"""
Exact length of compressed data could be found by decompressing gzip+footer
(which will automatically detect and strip the footer) and compressing it
back with same compression level. This approach is extremely slow and the
bigger the source file the longer it takes to recompress it:
GZIP_ARCHIVE_SIZE=`gzip -dc image.tmp 2>/dev/null | gzip -9 |wc -c`
(https://github.com/DeckerSU/kernel_zimage_unpack/blob/master/unpack.sh#L19)

Instead, we can find use faster method. In the end of any GZIP file is a
4 bytes long field for the size of decompressed data. If we decompress
out kernel.gz just once we can use this size to find GZIP end offset.
Ref: http://formats.kaitai.io/gzip/gzip.svg (we look for len_uncompressed)

Unlike UNIX `gzip`, python3 `gzip` module can't ignore "trailing garbage".
`zlib` module is used instead but it doesn't expect to stumble on GZ header so
skip it.  Used 'approach 5' from question: https://stackoverflow.com/q/4928560
"""
GZ_HDR_SZ = 10
kernel_sz = len(zlib.decompress(
    zimage[gz_off_start+GZ_HDR_SZ:], -zlib.MAX_WBITS))

GZ_LEN_UNCOMPR = kernel_sz.to_bytes(4, byteorder='little')
gz_off_end = where_is(GZ_LEN_UNCOMPR, zimage, reverse=True)
if gz_off_end == -1:
    exit("Couldn't find len_uncompressed field in file")
gz_off_end += 4  # Add field width (4 bytes) to its start offset

with open("1_kernel_header.bin", "wb") as f:
    f.write(zimage[:gz_off_start])
with open("2_kernel_image.gz", "wb") as f:
    f.write(zimage[gz_off_start:gz_off_end])
with open("3_kernel_footer.bin", "wb") as f:
    f.write(zimage[gz_off_end:])

print(f"""GZ starts at:         {gz_off_start}
GZ ends at:           {gz_off_end}
Decompressed size:    {kernel_sz}""")
