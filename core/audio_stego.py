import wave
import struct
from pathlib import Path

MAGIC = b"AUDSTEG1"  # 8-byte magic
HEADER_LEN = len(MAGIC) + 8  # magic + 8-byte payload length (uint64)
BITS_PER_SAMPLE_USED = 1     # number of LSBs used per sample (1 is safest)

def _read_wav_16bit(path: Path):
    with wave.open(str(path), 'rb') as w:
        n_channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        n_frames = w.getnframes()
        comptype = w.getcomptype()

        if sampwidth != 2:
            raise ValueError("Only 16-bit PCM WAV supported.")
        if comptype != 'NONE':
            raise ValueError("Compressed WAV not supported.")

        frames = w.readframes(n_frames)
    fmt = "<" + ("h" * (len(frames) // 2))
    samples = list(struct.unpack(fmt, frames))
    return samples, n_channels, framerate

def _write_wav_16bit(path: Path, samples, n_channels, framerate):
    print(f"[DEBUG] Writing WAV to: {path.resolve()}")
    samples_clamped = [int(max(min(s, 32767), -32768)) for s in samples]
    fmt = "<" + ("h" * len(samples_clamped))
    frames = struct.pack(fmt, *samples_clamped)

    with wave.open(str(path), 'wb') as w:
        w.setnchannels(n_channels)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(frames)


def _bytes_to_bits(data: bytes):
    for byte in data:
        for i in range(8):
            yield (byte >> (7 - i)) & 1

def _bits_to_bytes(bits):
    out = bytearray()
    b = 0
    count = 0
    for bit in bits:
        b = (b << 1) | (bit & 1)
        count += 1
        if count == 8:
            out.append(b)
            b = 0
            count = 0
    if count != 0:
        b = b << (8 - count)
        out.append(b)
    return bytes(out)

def _build_header(payload_len: int) -> bytes:
    return MAGIC + payload_len.to_bytes(8, 'big')

def _parse_header(header_bytes: bytes) -> int:
    if header_bytes[:len(MAGIC)] != MAGIC:
        raise ValueError("Invalid magic; not our stego.")
    return int.from_bytes(header_bytes[len(MAGIC):len(MAGIC)+8], 'big')

def embed_audio_lsb(cover_wav: str, payload_path: str, output_wav: str, bits_per_sample: int = BITS_PER_SAMPLE_USED):
    samples, n_channels, framerate = _read_wav_16bit(Path(cover_wav))
    payload = Path(payload_path).read_bytes()
    header = _build_header(len(payload))
    full = header + payload

    total_bits = len(full) * 8
    capacity_bits = len(samples) * bits_per_sample
    if total_bits > capacity_bits:
        raise ValueError("Payload too large for cover audio.")

    bit_iter = _bytes_to_bits(full)
    out_samples = samples[:]
    mask_clear = ~((1 << bits_per_sample) - 1)

    for i in range(total_bits):
        bit = next(bit_iter)
        s = out_samples[i]
        s = (s & mask_clear) | bit
        out_samples[i] = s

    _write_wav_16bit(Path(output_wav), out_samples, n_channels, framerate)

def extract_audio_lsb(stego_wav: str, output_payload: str, bits_per_sample: int = BITS_PER_SAMPLE_USED):
    samples, n_channels, framerate = _read_wav_16bit(Path(stego_wav))

    header_bits_count = HEADER_LEN * 8
    bits = [samples[i] & 1 for i in range(header_bits_count)]
    header_bytes = _bits_to_bytes(bits)[:HEADER_LEN]
    payload_len = _parse_header(header_bytes)

    payload_bits_count = payload_len * 8
    bits = [samples[i] & 1 for i in range(header_bits_count, header_bits_count + payload_bits_count)]
    payload_bytes = _bits_to_bytes(bits)[:payload_len]

    Path(output_payload).write_bytes(payload_bytes)
