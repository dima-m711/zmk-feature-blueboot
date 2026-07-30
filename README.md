# Blueboot

Blueboot is a reusable ZMK module that reboots an Adafruit nRF52 bootloader
directly into Bluetooth DFU mode. It also includes a packaging tool that turns
a ZMK UF2 or Intel HEX image into a Nordic Secure DFU ZIP.

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

The first Blueboot-enabled firmware must be installed over USB.

## Package firmware

Before using BLE DFU, open `INFO_UF2.TXT` on the bootloader drive and verify its
SoftDevice version. The defaults below target S140 7.3.0, firmware ID `0x0123`.

Install the packaging dependency:

```sh
python -m pip install adafruit-nrfutil
```

Create a DFU ZIP from a ZMK UF2:

```sh
python modules/zmk-feature-blueboot/scripts/blueboot.py path/to/zmk.uf2
```

The command creates `zmk-blueboot.zip` next to the input when the input is named
`zmk.uf2`. An Intel HEX image can be used in the same way. Override the
compatibility values only when the installed bootloader requires them:

```sh
python modules/zmk-feature-blueboot/scripts/blueboot.py \
  --sd-req 0x0123 \
  --dev-type 0x0052 \
  path/to/zmk.uf2
```

Keep the USB UF2 as a recovery image in case a BLE transfer is interrupted.

## Perform an OTA update

1. Prepare a DFU ZIP for each half of the keyboard.
2. Press the key bound to `&blueboot` on the half to update.
3. Open Nordic Semiconductor's **nRF Device Firmware Update** app.
4. Select the DFU ZIP and the target advertised by the bootloader.
5. Start the transfer and wait for the half to reboot into ZMK.
6. Repeat the process from the other half for a split keyboard.

Never update both halves at the same time. Connect the target half to USB or
make sure its battery has enough charge before starting.

## Recover from an interrupted transfer

The normal Adafruit bootloader may not return to BLE DFU after a transfer has
already erased or invalidated the application. The
[OTAFIX bootloader](https://github.com/oltaco/Adafruit_nRF52_Bootloader_OTAFIX)
changes this behavior: when no valid application exists, a reset returns the
board to BLE DFU automatically.

With OTAFIX installed:

- A successful transfer boots ZMK normally.
- If a transfer is interrupted after the application becomes invalid, reset
  the board and reconnect to `XIAO_DFU` to retry.
- If the previous application is still valid, the board may boot ZMK instead.
  Press `&blueboot` again to retry.
- To request the USB UF2 drive explicitly, double-reset the board.

### Install OTAFIX on XIAO nRF52840

Perform these steps on one half at a time:

1. Connect the XIAO to USB.
2. Double-reset it within about 0.5 seconds to expose the UF2 drive. On a board
   without a reset button, briefly short `RST` to `GND` twice.
3. Open `INFO_UF2.TXT` on the drive and check `Board-ID`.
4. Download the matching `update-..._nosd.uf2` file from the
   [latest OTAFIX release](https://github.com/oltaco/Adafruit_nRF52_Bootloader_OTAFIX/releases/latest):
   - `Board-ID: nRF52840-SeeedXiaoSense-v1`: use
     `update-xiao_nrf52840_ble_sense_bootloader-..._nosd.uf2`.
   - Other XIAO nRF52840 BLE Board-IDs: use
     `update-xiao_nrf52840_ble_bootloader-..._nosd.uf2`.
5. Copy the update UF2 to the bootloader drive and wait for the board to reset.
6. Repeat for the other half.

Some non-Sense XIAO boards ship with a Sense bootloader. Select the update from
`INFO_UF2.TXT`, not from the product name or appearance. Installing the wrong
variant can require an SWD programmer to recover.

### Return to the standard bootloader

OTAFIX can normally be replaced over USB without an SWD programmer:

1. Double-reset to expose the UF2 drive.
2. Check `INFO_UF2.TXT` again.
3. Download the matching `update-xiao_nrf52840_ble..._nosd.uf2` from the
   [standard Adafruit nRF52 bootloader releases](https://github.com/adafruit/Adafruit_nRF52_Bootloader/releases/latest).
4. Copy it to the UF2 drive and wait for the board to reset.

This returns the board to the standard Adafruit bootloader, which is not
necessarily byte-for-byte identical to the factory Seeed bootloader. Returning
also removes OTAFIX's automatic BLE DFU fallback after a failed transfer.

## Troubleshooting

- **No USB drive or serial port after a failed OTA:** OTAFIX may be waiting in
  BLE DFU mode. Look for `XIAO_DFU`, or double-reset to force USB UF2 mode.
- **The DFU app reports `Operation Failed` near the start:** retry with
  **Request high MTU** disabled. Trying a smaller PRN value can also help.
- **The board boots ZMK instead of staying in DFU:** the application is still
  valid. Invoke `&blueboot` again.
- **The DFU package is rejected:** verify the SoftDevice ID in `INFO_UF2.TXT`.
  Blueboot's packaging default is `0x0123` for S140 7.3.0.
- **The halves will not reconnect after updating only one side:** install
  matching ZMK builds on both halves over USB, then pair them again if needed.

## 日本語ガイド

### 1. ZMKへBluebootを追加する

`config/west.yml`へこのモジュールを追加し、キーマップで次のファイルを読み込みます。

```dts
#include <behaviors/blueboot.dtsi>
```

OTA開始用のキーには次を割り当てます。

```dts
&blueboot
```

分割キーボードでは、実際に押した側だけがBLE DFUモードへ入ります。最初の
Blueboot対応ファームウェアはUSBで左右それぞれに書き込んでください。

### 2. OTA用ZIPを作る

```sh
python -m pip install adafruit-nrfutil
python modules/zmk-feature-blueboot/scripts/blueboot.py path/to/zmk.uf2
```

入力が `zmk.uf2` なら、同じ場所に `zmk-blueboot.zip` が作られます。標準設定は
SoftDevice S140 7.3.0、firmware ID `0x0123` 用です。USBのブートローダードライブに
ある `INFO_UF2.TXT` でSoftDeviceを確認してください。

### 3. OTAで更新する

1. 更新する側で `&blueboot` のキーを押します。
2. スマートフォンの **nRF Device Firmware Update** を開きます。
3. 対応する側のDFU ZIPとブートローダーのデバイスを選択します。
4. 転送を開始し、ZMKが再起動するまで待ちます。
5. 反対側も同じ手順で更新します。

左右の同時更新は避け、必ず片側ずつ行ってください。

### 4. OTA失敗時に自動復帰できるようにする

[OTAFIXの最新リリース](https://github.com/oltaco/Adafruit_nRF52_Bootloader_OTAFIX/releases/latest)
から対応する `update-..._nosd.uf2` を入れます。

1. XIAOをUSB接続します。
2. 約0.5秒以内にリセットを2回押してUF2ドライブを表示します。リセットボタンが
   なければ `RST` と `GND` を素早く2回ショートします。
3. `INFO_UF2.TXT` の `Board-ID` を確認します。
4. `nRF52840-SeeedXiaoSense-v1` ならSense版、それ以外なら通常BLE版の
   `update-..._nosd.uf2` をUF2ドライブへコピーします。
5. 再起動したら反対側にも同じ作業を行います。

非SenseのXIAOでもSense用ブートローダーが入っている個体があります。製品名や
外観ではなく、必ず `INFO_UF2.TXT` に合わせてください。

OTAFIX導入後の挙動は次のとおりです。

- OTA成功: 新しいZMKが通常起動します。
- OTA途中失敗・アプリ無効: リセットすると `XIAO_DFU` としてOTA待機へ戻ります。
- 旧アプリが有効: ZMKが起動するので、もう一度 `&blueboot` を押します。
- USBで復旧したい: ダブルリセットしてUF2を表示し、保存しておいたZMK UF2を
  コピーします。

### 5. 標準ブートローダーへ戻す

1. ダブルリセットしてUF2ドライブを表示します。
2. `INFO_UF2.TXT` で通常版かSense版かを確認します。
3. [Adafruit標準ブートローダーの最新リリース](https://github.com/adafruit/Adafruit_nRF52_Bootloader/releases/latest)
   から対応する `update-xiao_nrf52840_ble..._nosd.uf2` をダウンロードします。
4. UF2ドライブへコピーし、再起動を待ちます。

通常はSWDライターなしで戻せます。ただし、これはAdafruit標準版への復帰であり、
Seeed工場出荷時の内容と完全に同一とは限りません。また、標準版へ戻すとOTA失敗後
にBLE DFUへ自動復帰する機能はなくなります。

## License

[MIT](LICENSE)
