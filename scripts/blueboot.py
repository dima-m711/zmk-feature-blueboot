#!/usr/bin/env python3
"""Create an Adafruit/nRF52 BLE DFU package from a ZMK HEX or UF2 image."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

UF2_BLOCK_SIZE = 512
UF2_MAGIC_START_0 = 0x0A324655
UF2_MAGIC_START_1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
UF2_FLAG_NO_FLASH = 0x00000001


def parse_int(value: str) -> int:
    return int(value, 0)


def read_uf2(path: Path) -> dict[int, int]:
    raw = path.read_bytes()
    if not raw or len(raw) % UF2_BLOCK_SIZE:
        raise ValueError(f"{path} is not a complete UF2 image")

    image: dict[int, int] = {}
    for offset in range(0, len(raw), UF2_BLOCK_SIZE):
        block = raw[offset : offset + UF2_BLOCK_SIZE]
        (
            magic0,
            magic1,
            flags,
            target_address,
            payload_size,
            _block_number,
            _block_count,
            _family_or_file_size,
        ) = struct.unpack_from("<8I", block)
        magic_end = struct.unpack_from("<I", block, UF2_BLOCK_SIZE - 4)[0]

        if (
            magic0 != UF2_MAGIC_START_0
            or magic1 != UF2_MAGIC_START_1
            or magic_end != UF2_MAGIC_END
        ):
            raise ValueError(f"{path} contains an invalid UF2 block at offset {offset}")
        if flags & UF2_FLAG_NO_FLASH:
            continue
        if payload_size > 476:
            raise ValueError(f"{path} contains an oversized UF2 payload")

        payload = block[32 : 32 + payload_size]
        for index, value in enumerate(payload):
            address = target_address + index
            previous = image.setdefault(address, value)
            if previous != value:
                raise ValueError(f"{path} contains conflicting data at address 0x{address:08x}")

    if not image:
        raise ValueError(f"{path} has no flashable UF2 data")
    return image


def ihex_record(address: int, record_type: int, data: bytes) -> str:
    body = bytes((len(data), (address >> 8) & 0xFF, address & 0xFF, record_type)) + data
    checksum = (-sum(body)) & 0xFF
    return ":" + (body + bytes((checksum,))).hex().upper()


def write_ihex(image: dict[int, int], destination: Path) -> None:
    addresses = sorted(image)
    lines: list[str] = []
    current_upper: int | None = None
    cursor = 0

    while cursor < len(addresses):
        start = addresses[cursor]
        upper = start >> 16
        if upper != current_upper:
            lines.append(ihex_record(0, 4, upper.to_bytes(2, "big")))
            current_upper = upper

        chunk = bytearray((image[start],))
        cursor += 1
        while (
            cursor < len(addresses)
            and addresses[cursor] == start + len(chunk)
            and addresses[cursor] >> 16 == upper
            and len(chunk) < 16
        ):
            chunk.append(image[addresses[cursor]])
            cursor += 1

        lines.append(ihex_record(start & 0xFFFF, 0, bytes(chunk)))

    lines.append(ihex_record(0, 1, b""))
    destination.write_text("\n".join(lines) + "\n", encoding="ascii")


def resolve_nrfutil(requested: str) -> str:
    candidate = Path(requested)
    if candidate.parent != Path(".") and candidate.exists():
        return str(candidate.resolve())

    resolved = shutil.which(requested)
    if resolved:
        return resolved

    raise FileNotFoundError(
        f"{requested!r} was not found. Install it with "
        "`python -m pip install adafruit-nrfutil`, or pass --nrfutil PATH."
    )


def validate_package(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError(f"DFU package was not created: {path}")

    with zipfile.ZipFile(path) as archive:
        members = set(archive.namelist())
        if "manifest.json" not in members:
            raise RuntimeError("DFU package is missing: manifest.json")

        manifest = json.load(archive.open("manifest.json"))
        application = manifest.get("manifest", {}).get("application", {})
        required = {
            application.get("bin_file", ""),
            application.get("dat_file", ""),
        } - {""}
        missing = required - members
        if missing:
            raise RuntimeError(f"DFU package is missing: {', '.join(sorted(missing))}")
        if len(required) != 2:
            raise RuntimeError("DFU package manifest has no complete application image")
        if archive.testzip() is not None:
            raise RuntimeError(f"DFU package failed its ZIP integrity check: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="blueboot",
        description="Package a ZMK HEX or UF2 image for Adafruit nRF52 BLE OTA.",
    )
    parser.add_argument("firmware", type=Path, help="ZMK .hex or .uf2 firmware image")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output ZIP path (default: FIRMWARE-blueboot.zip)",
    )
    parser.add_argument(
        "--sd-req",
        type=parse_int,
        default=0x0123,
        help="SoftDevice firmware ID accepted by the package (default: 0x0123, S140 7.3.0)",
    )
    parser.add_argument(
        "--dev-type",
        type=parse_int,
        default=0x0052,
        help="Nordic device type (default: 0x0052, nRF52840)",
    )
    parser.add_argument(
        "--nrfutil",
        default=os.environ.get("ADAFRUIT_NRFUTIL", "adafruit-nrfutil"),
        help="adafruit-nrfutil executable name or path",
    )
    args = parser.parse_args()

    firmware = args.firmware.resolve()
    if not firmware.is_file():
        parser.error(f"firmware does not exist: {firmware}")
    if firmware.suffix.lower() not in {".hex", ".uf2"}:
        parser.error("firmware must use the .hex or .uf2 extension")

    output = (
        args.output.resolve()
        if args.output
        else firmware.with_name(f"{firmware.stem}-blueboot.zip")
    )
    if output == firmware:
        parser.error("output must differ from the input firmware")
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        nrfutil = resolve_nrfutil(args.nrfutil)
        with tempfile.TemporaryDirectory(prefix="blueboot-") as temporary:
            if firmware.suffix.lower() == ".uf2":
                application = Path(temporary) / f"{firmware.stem}.hex"
                write_ihex(read_uf2(firmware), application)
            else:
                application = firmware

            command = [
                nrfutil,
                "dfu",
                "genpkg",
                "--dev-type",
                f"0x{args.dev_type:04x}",
                "--sd-req",
                f"0x{args.sd_req:04x}",
                "--application",
                str(application),
                str(output),
            ]
            subprocess.run(command, check=True)
        validate_package(output)
    except (FileNotFoundError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Created Blueboot package: {output}")
    print(f"SoftDevice requirement: 0x{args.sd_req:04x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
