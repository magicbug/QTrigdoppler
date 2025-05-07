# QT RigDoppler


<picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
 <source media="(prefers-color-scheme: light)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
 <img alt="Shows QTRigDoppler GUI." src="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
</picture> 

## RigDoppler features doppler shift control for ICOM radios.

Based on K8DP Doug Papay rigdoppler (@K8DP_Doug)  
Adapted v0.3 and QT by EA4HCF Pedro Cabrera (@PCabreraCamara)  
Extended and modified by DL3JOP Joshua Petry (@dl3jop)

Attention: I'm looking for bug reports and new features. Every pull-request/issue is welcomed.<br/>
Note: Read the Readme regarding setup and initial installation.<br/>
Note: The software is tested on my two IC-910H (EU as well as US version). The IC-9700 should work as well but I did not check that. Please report your findings!<br/>

## Installation guide
### Ubuntu 24.10 or higher
 1) It is assumed that you use Ubuntu 24.10 (or newer) or a derivative of it
 2) Open a terminal
 3) Update package sources by:<br/> `sudo apt update`
 5) Install required packages:<br/> `sudo apt install git python3 python3-pyqt5 python3-qt-material python3-ephem python3-numpy`
 6) Add your user to the dialout group to access the serial port by:<br/> `sudo adduser [username, remove brackets] dialout` e.g.: `sudo adduser dl3jop dialout`<br/>
 6.1) Restart you computer for all changes to take effect, than repeat step 2)<br/>
 7) Get the software by:<br/> `git clone https://github.com/dl3jop/QTrigdoppler.git`
 8) Enter software directory by:<br/> `cd QTrigdoppler`
 9) Start using:<br/> `python3 QTrigdoppler.py`
 10) For every startup from now on repeat step 2,7 and 8 or create a starter in the start menu

 11) TLDR:\
     `sudo apt update`\
     `sudo apt install git python3 python3-pyqt5 python3-qt-material python3-ephem python3-numpy`\
     `sudo adduser [username, remove brackets] dialout`\
     `git clone https://github.com/dl3jop/QTrigdoppler.git`\
     `python3 QTrigdoppler.py`

### Arch or derivatives (e.g.: Manjaro)
`sudo pacman -Syu`\
     `sudo pacman -S git python python-pyqt5 python-qt-material python-ephem python-numpy`\
     `sudo usermod -aG uucp [username, remove brackets]`\
     `git clone https://github.com/dl3jop/QTrigdoppler.git`\
     `python3 QTrigdoppler.py`

## Requirements for using the map:  
Currently, using the map is not advised due to bad perfomance. If you choose to try it, you'll need:<br/>
`matplotlib
cartopy
pyproj`
  
    
# Basic Configuration:
<picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
 <source media="(prefers-color-scheme: light)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
 <img alt="Shows the GUI for editing config." src="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
</picture> 

## Configuration notes

1) maximum and minimun values for RX and TX offset (Hertz) can be adjusted if the per device drift should exceed the normal range.<br/>

2) tle_file must contain ephemeris two line elements to calculate satellite passes over the coordinates in the [qth] section. <br/>

3) sqffile must contain satellites' frequencies (both downlink and uplink), following the same format as the original SatPC32 file. <br/>

4) Doppler Thresholds:
     - Select the thresholds for FM/SSB doppler correction. Frequencies are not updated when the difference between the current doppler frequency and radio frequency is below the threshold.
5) Offset Profiles:
    - Offsets will be automatically loaded when selecting the satellite. Satellite and transponder name must be the same as in the doppler.sqf file:
      satoffset1 = IO-117,Digipeater,-750,-750
      where IO-117 is the the satellites name, Digipeater the description/transponder and the two numbers RX/TX offset.
## Attention:
After installation/download you need to adjust `config.ini` to suit your needs. If you have a US configured IC-910 you need to change the `rig_type` from `EU` to `US` otherwise TSL or T won't work
You might also need to change the serial port of your CI-V to serial adapter. The easiest solution is to run `sudo dmesg -wH` in a terminal and plugging in your serial adpter to get the serial port name.
Portnames might be `/dev/ttyUSB0`, `/dev/ttyUSB1` .... or `/dev/tty/ACM0` ... 

# Changelog
DL3JOP modifications: <br/>
    1) Removed hamlib<br/>
    2) support for IC-910H by direct serial communication, IC-9700 should work as well (not yet tested)<br/>
    3) Implemented transponder selection<br/>
    4) Implemented correct switch between Split mode for V/V & U/U packet and satmode for V/U,U/V<br/>
    5) Implemented doppler correction threshold<br/>
    6) Added SubTone control<br/>
    7) Various smaller changes and additions<br/>
    8) Added binaries
    
# Roadmap:
  - Adding support for IC-9700 (should be easy as it uses nearly the same comands as the IC-910H)
  - Adding support for FT-8xx radios. Same approch: serial driver, although that will add additonal reworks in the doppler tracking loop to account for two radios
  - Building a much nicer GUI
  - Separate GUI and tracking class
  - Refactor tracking loop:
    - no global F0/I0 variables, more abstracted methods to allow eaier implementation of other radios
    
# Developer notes
## Compile using pyinstaller
`pyinstaller --onefile QTrigdoppler.py --exclude PySide6 --exclude PyQt6 --splash images/splash.jpg`
