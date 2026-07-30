# Blueboot

Blueboot is a reusable ZMK module that reboots an Adafruit nRF52 bootloader
directly into Bluetooth DFU mode. It also includes a small packaging tool that
turns a ZMK UF2 or Intel HEX image into a Nordic Secure DFU ZIP.

The module is intended for nRF52 boards running the Adafruit nRF52 bootloader,
including `seeeduino_xiao_ble`. It uses the bootloader's `0xA8` GPREGRET request
and supports both older ZMK/Zephyr releases and the newer boot-mode retention
API.

## Install

Add the module to the ZMK config repository's `config/west.yml`:

```yaml
manifest:
  projects:
    - name: zmk-feature-blueboot
      url: https://github.com/te9no/zmk-feature-blueboot
      revision: main
      path: modules/zmk-feature-blueboot
```

Include the predefined behavior in the keymap:

```dts
#include <behaviors/blueboot.dtsi>
```

Then bind it like any other zero-parameter ZMK behavior:

```dts
&blueboot
```

On a split keyboard, Blueboot uses `BEHAVIOR_LOCALITY_EVENT_SOURCE`. A binding
pressed on the left half reboots the left half, while a binding pressed on the
right half reboots the right half.

## Package firmware

The first Blueboot-enabled firmware must be installed over USB. Before using
BLE DFU, open `INFO_UF2.TXT` on the bootloader drive and verify its SoftDevice
version. The defaults below target S140 7.3.0, firmware ID `0x0123`.

Install the packaging dependency:

```sh
python -m pip install adafruit-nrfutil
```

Create a DFU ZIP from a ZMK UF2:

```sh
python modules/zmk-feature-blueboot/scripts/blueboot.py path/to/zmk.uf2
```

The command creates `zmk-blueboot.zip`. Override the compatibility values only
when the installed bootloader requires them:

```sh
python modules/zmk-feature-blueboot/scripts/blueboot.py \
  --sd-req 0x0123 \
  --dev-type 0x0052 \
  path/to/zmk.uf2
```

Keep the USB UF2 as a recovery image in case a BLE transfer is interrupted.

## 日本語

Bluebootは、Adafruit nRF52 BootloaderをZMKのキー操作から直接BLE DFUモードへ
再起動するための外部モジュールです。分割キーボードではキーイベントが発生した
側だけを再起動できるため、左右を個別に更新できます。

最初のBlueboot対応ファームウェアだけはUSBで書き込む必要があります。BLE更新を
始める前に、ブートローダードライブの `INFO_UF2.TXT` でSoftDeviceを確認して
ください。標準設定はS140 7.3.0（firmware ID `0x0123`）向けです。

## License

[MIT](LICENSE)
