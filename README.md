# ⌨ Ladispad
[![Visits Badge](https://badges.pufler.dev/visits/ajmandourah/Ladispad)](https://badges.pufler.dev) [![GitHub license](https://img.shields.io/github/license/ajmandourah/Ladispad)](https://github.com/ajmandourah/Ladispad/blob/main/LICENSE) [![GitHub forks](https://img.shields.io/github/forks/ajmandourah/Ladispad)](https://github.com/ajmandourah/Ladispad/network) ![GitHub all releases](https://img.shields.io/github/downloads/ajmandourah/Ladispad/total)

Ladispad is a custom-made 11 key macropad with 2 rotary encoders designed for the **simplicity** and the **ease of assembly for non technical users**. 
Macropads are not a new thing. Browsing the internet will lead to to dozens of open-source macropads that let you print your own PCB and assemble it at home, but most of these macropads use matrixes, which will force you to solder diodes adding a little complexity to the process.

Ladispad uses a **direct pin** approach. That means you **don't need to solder diodes**. Additionally, I managed to add 2 rotary encoders and a fully customizable OLED screen, which can be omitted if you choose.

Ladispad uses a Pro Micro as its main controller. It's very affordable, and there are many variants with different USB ports and sizes. **I designed the PCB so it will be compatible which whatever you choose**.

![Ladispad PCB showing promicro compatibility](/images/IMG-20211108-WA0001.jpg) 

Ladispad supports QMK/VIA and includes a Vial keymap for configuring keys, layers, encoder actions, and macros without reflashing.

Included are the SVG files for the acrylic cases I made for the pad. You can laser cut it using the online service provider of your choice.

## 👍 What makes the Ladispad unique: 

- Minimal components needed to have a fully functional macropad
- 2 Rotary encoders implemented with extra function with layer switching
- Compatible with different Pro Micro sizes
- Acrylic case cutout included

## 📃 Things you need to get the whole experience:

- Pro Micro (micro USB, mini USB, USB-C)
- 9 cherry MX style switches
- 2 Rotary Encoders (EC11)
- OLED display 128x32 (SSD1306)
- The laser cut acrylic case
- 4 M3 screws

## ⁉ How to make your own:

- Ordering the PCB
  - Download the Gerber.zip file from the release page
  - Order the PCB from a PCB manufacturer site, I have used PCBway and it cost 5$ + shipping for 5 PCBs
- Making the Case
  - Download the case.zip file from the release page
  - Submit the files to a laser cutting service provider, or cut it yourself if you are blessed with a laser cutter. I can recommend Elecrow, pretty cheap and reliable.
  - The thickness of the parts is as follows:
    - The top and bottom layers are **3 mm**
    - The middle layers (middle layer 1 and middle layer 2) are **8 mm**
- Buy the parts listed above
- Solder the Pro Micro, switches, rotary encoders, and the OLED screen
- Either download the hex file from the release page and flash it before assembling the case (short the RESET and GND pins as I have not added a dedicated reset button, will be added in the future), or you can also edit the QMK keymap file in the repo for more customizability. Clone the repo if that is the case.
- Enjoy your new macropad

## 📷 Images:

![](/images/20211129_065114-01.jpeg) 
![](/images/20211129_065213-01.jpeg)
![](/images/20211129_065248-01.jpeg)

## Firmware development and Vial

The keyboard source is in `qmk/ladis`. This Pro Micro uses the **Caterina** bootloader, set in `qmk/ladis/keyboard.json`. The Vial keymap enables the OLED and displays `LADISPAD` plus the active Vial layer number (`0`–`3`). It disables optional QMK features to leave room for Vial and the display in the ATmega32U4's flash.

### Build locally

Set up a local Vial-QMK environment and build the Vial keymap:

```sh
./scripts/setup.sh
./scripts/build.sh vial
```

The artifact is `build/ladis_vial.hex`. Setup uses a separate `~/Development/vial-qmk` checkout and does not replace an existing `qmk_firmware` checkout. Local compilation requires AVR GCC; if it's missing, run `./scripts/build_avr_toolchain.sh` once. `./scripts/flash.sh vial` builds first, then waits for the bootloader—double-reset the Pro Micro when the flash step is waiting.

### Build with GitHub Actions

Pushes and pull requests that change `qmk/ladis` automatically build Vial firmware. To start a build manually, open the repository's **Actions** tab and select **Build Ladispad Vial firmware → Run workflow**. Download the `ladis-vial-<commit>` artifact from the run; it contains `ladis_vial.hex`. Actions builds the firmware but cannot flash a USB-connected pad.

### Flash a downloaded artifact

On macOS, start this command with the downloaded HEX path, then double-reset the Pro Micro. The command waits for Caterina's temporary `/dev/cu.usbmodem*` port and flashes as soon as it appears:

```sh
HEX="$HOME/Downloads/ladis_vial.hex" # set this to the downloaded file
while :; do
  PORT=""
  for candidate in /dev/cu.usbmodem*; do
    [[ -e "$candidate" ]] && { PORT="$candidate"; break; }
  done
  [[ -n "$PORT" ]] && break
  sleep 0.1
done
avrdude -p atmega32u4 -c avr109 -P "$PORT" -b 57600 -U "flash:w:${HEX}:i"
```

With USB connected, briefly bridge the Pro Micro's **RST** and **GND** pins twice, releasing between touches; make the second touch within about 750 ms. Caterina stays available for only a few seconds, so don't hold the bridge. A successful flash reports that the bytes were written and verified, then the pad re-enumerates as `LadisPad`. QMK Toolbox is another option for flashing the HEX.

Open [Vial](https://get.vial.today/) and connect the pad. Hold the top-middle and top-right keys together to unlock it. The OLED shows the active Vial layer (`0`–`3`); assign `MO(1)` to a spare key and hold it to test layer 1. To test a macro, create one with Tap `O`, Tap `K`, then Tap `Down`, and assign it to the top-left key. Vial changes are saved on the device, so remapping does not require reflashing.

## Update the layer images

To create your own images for a layer create an image file with 128×32 dimension.
Upload the file to https://joric.github.io/qle/ and use the `raw data` representation in the `keymap.c` file 

``` c
static const char PROGMEM raw_logo[] = {
       $RAW_IMAGE
};
```

Now compile and upload the firmware again and the new images should be displayed.