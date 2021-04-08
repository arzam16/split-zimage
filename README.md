# split-zimage
This script splits extracted zImage into parts. After splitting it's possible to obtain the Linux kernel binary by decompressing the '2_kernel_image.gz' file.

_Insipred by [DeckerSU's unpack.sh](https://github.com/DeckerSU/kernel_zimage_unpack) and actually runs much faster than it!_

## Usage
`split-zimage.py boot.img-zImage`

## Intended workflow
1. Unpack the boot.img with AIK-Linux
2. **Feed boot.img-zImage to this script**
3. Decompress 2_kernel_image.gz
4. Do further modifications

## Limitations
* Supports GZIP compression only
