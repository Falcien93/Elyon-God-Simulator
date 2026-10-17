"""Sample a HighResShot PNG and flag an all-black or all-white frame."""

import os
import struct
import zlib

BLACK_LUMA = 12.0
WHITE_LUMA = 243.0
EXTREME_FRACTION = 0.98
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def classify_lumas(lumas, black_max=BLACK_LUMA, white_min=WHITE_LUMA, extreme_fraction=EXTREME_FRACTION):
    """Return black, white, ok, or empty.

    A few bright gizmo pixels do not rescue a black frame. The call is black
    when almost every sample is near luma 0, and white when almost every
    sample is near luma 255.
    """
    values = list(lumas)
    count = len(values)
    if count == 0:
        return "empty"
    dark = sum(1 for value in values if value <= black_max)
    bright = sum(1 for value in values if value >= white_min)
    if dark / count >= extreme_fraction:
        return "black"
    if bright / count >= extreme_fraction:
        return "white"
    return "ok"


def _paeth(left, up, upper_left):
    estimate = left + up - upper_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_upper_left = abs(estimate - upper_left)
    if distance_left <= distance_up and distance_left <= distance_upper_left:
        return left
    if distance_up <= distance_upper_left:
        return up
    return upper_left


def _unfilter(filter_type, row, previous, channels):
    width_bytes = len(row)
    if filter_type == 0:
        return row
    if filter_type == 1:
        for index in range(width_bytes):
            left = row[index - channels] if index >= channels else 0
            row[index] = (row[index] + left) & 255
        return row
    if filter_type == 2:
        for index in range(width_bytes):
            row[index] = (row[index] + previous[index]) & 255
        return row
    if filter_type == 3:
        for index in range(width_bytes):
            left = row[index - channels] if index >= channels else 0
            row[index] = (row[index] + ((left + previous[index]) // 2)) & 255
        return row
    if filter_type == 4:
        for index in range(width_bytes):
            left = row[index - channels] if index >= channels else 0
            upper_left = previous[index - channels] if index >= channels else 0
            row[index] = (row[index] + _paeth(left, previous[index], upper_left)) & 255
        return row
    raise ValueError(f"unsupported png filter {filter_type}")


def png_rgb_samples(data, stride=32):
    """Return width, height, and strided RGB samples from an 8-bit PNG."""
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a png")
    position = 8
    width = height = None
    bit_depth = color_type = interlace = None
    compressed = bytearray()
    while position + 8 <= len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        payload = data[position + 8 : position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _compression, _filter, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    if width is None or height is None or interlace:
        raise ValueError("unsupported png")
    if bit_depth != 8 or color_type not in (2, 6):
        raise ValueError("unsupported png")
    channels = 3 if color_type == 2 else 4
    raw = zlib.decompress(bytes(compressed))
    row_bytes = width * channels
    samples = []
    previous = bytearray(row_bytes)
    offset = 0
    step = max(1, int(stride))
    for y in range(height):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset : offset + row_bytes])
        offset += row_bytes
        row = _unfilter(filter_type, row, previous, channels)
        previous = row
        if y % step:
            continue
        for x in range(0, width, step):
            index = x * channels
            samples.append((row[index], row[index + 1], row[index + 2]))
    return width, height, samples


def classify_png(data, stride=32):
    _width, _height, samples = png_rgb_samples(data, stride=stride)
    lumas = [(red + green + blue) / 3.0 for red, green, blue in samples]
    return classify_lumas(lumas), lumas


def write_rgb_png(width, height, pixel_at):
    """Filter-0 RGB PNG. pixel_at(x, y) returns red, green, blue."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            red, green, blue = pixel_at(x, y)
            raw.extend((red & 255, green & 255, blue & 255))

    def chunk(tag, payload):
        crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    body = zlib.compress(bytes(raw))
    return PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", body) + chunk(b"IEND", b"")


def newest_png(root, not_before):
    """Newest PNG at or after not_before, or None."""
    if not root or not os.path.isdir(root):
        return None
    newest = None
    newest_mtime = not_before
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.lower().endswith(".png"):
                continue
            path = os.path.join(dirpath, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            if mtime + 1.0 < not_before:
                continue
            if newest is None or mtime >= newest_mtime:
                newest = path
                newest_mtime = mtime
    return newest
