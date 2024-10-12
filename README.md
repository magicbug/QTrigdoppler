# QT RigDoppler v0.4 (stable release for IC-910)

Based on K8DP Doug Papay rigdoppler (@K8DP_Doug)  
Adapted v0.3 and QT by EA4HCF Pedro Cabrera (@PCabreraCamara)  
Extended and modified to v0.4 by DL3JOP Joshua Petry (@dl3jop)
  
RigDoppler is a very simple Python3 script to correct doppler effect in radio satellites using Icom rigs connected to a computer.

Attention: I'm looking for bug reports and new features. Every pull-request/issue is welcomed

<picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
 <source media="(prefers-color-scheme: light)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
 <img alt="Shows QTRigDoppler GUI." src="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
</picture>  
  
## Requirements:  
    1) Python3  
    2) Python3 modules
       pip3 install ephem
       pip3 install PyQt5
       pip3 install urllib3
       pip3 install pyserial
  
Support files and download links:  

    1) TLE ephemerides file. (Example: https://tle.oscarwatch.org/)   
    2) AmsatNames.txt (https://www.ea5wa.com/satpc32/archivos-auxiliares-de-satpc32)   
    3) doppler.sqf (included)

  
AmsatNames.txt and dopler.sqf are wide and well known files used by SatPC32 software, so can be reused in the same computer.  

## v0.4 vs v0.3 and earlier (DL3JOP modifications):
    1) Removed hamlib
    2) support for IC-910H by direct serial communication
    3) Implemented transponder selection
    4) Implemented correct switch between Split mode for V/V & U/U packet and satmode for V/U,U/V
    5) Implemented doppler correction threshold
    
## Basic Configuration:
<picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
 <source media="(prefers-color-scheme: light)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
 <img alt="Shows the GUI for editing config." src="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
</picture>  
    1) "Setup" menu, "Edit setup" item to review and change the parameters:. QTH Parameters


    
    - Latitude, Longitude and altitude.
    - Step for RX and TX offset sliders (Hertz).
    - Maximun and minimun values for RX and TX offset sliders (Hertz).

    Satellite parameters:
    Support files used to get satellites frequencies and ephemeris:

    - tle_file must contain ephemeris two line elements to calculate satellite passes over the coordinates in the [qth] section.
    - sqffile must contain satellites' frequencies (both downlink and uplink), following the same format as the original SatPC32 file.
    - amsatnames is just an auxiliary file son NORAD_ID satellites identifiers could be correlated with common satellites names used in doppler.sf file. Three columns per each satellite will list NORAD_ID identifier and common satellite name.

    Doppler Thresholds:
    - select the thresholds for FM/SSB doppler correction. Frequencies are not updated when the difference between the current doppler frequency and radio frequency is below the threshold
    Offset Profiles:
    - Offsets will be automatically loaded when selecting the satellite. satellite and transponder name must be the same as in the doppler sqf file:
      satoffset1 = IO-117,Digipeater,-750,-750
      where IO-117 is the the satellites name, Digipeater the description/transponder and the two numbers RX/TX offset


        
  
  
  2) Execute RigDoppler: python3 /path/to/QTrigdoppler.py        
        
## Field Tests:

|     Radio     |   Satellite   |     Tester    |     Date    |
| ------------- | ------------- | ------------- | ----------- |
|  Icom 910H    |  RS-44        |     DL3JOP    |   Sep 24    |
|  Icom 910H    |  SO-50        |     DL3JOP    |   Sep 24    |
|  Icom 910H    |  ARISS        |     DL3JOP    |   Sep 24    |


## The good, the bad and the ugly - Feature/Bug Tracker

Although I tested v0.4 on multiple passes in FM as well as SSB, this project is still WIP. Please, please tell me which bugs you encounterd!
### Known bugs:
  - V/V U/V VFO exchange is only done when the PTT is not engaged. Otherwise the VFO might swap during TX as the IC-910 is not capable to change the unselected VFO. Nevertheless if the radio is put into TX right in between the PTT monitoring command and the VFO switch, the VFOs will mix up.
    - That might be resolvable by adding an TCP client/server which acts as an middle-man between the Terminal, e.g. Greencube Terminal and the modem, e.g. soundmodem to buffer TX messages while the frequency of VFOB is updated
  - Currently there is no support to enable/change SubTones. The icom library supporst it but I'm undecided how to store the parameters. Maybe similar to the offset profiles?
  - Storing the offset profiles sometimes adds empty lines, atm I don't know why   

## Roadmap:
  - Adding support for IC-9700 (should be easy as it uses nearly the same comands as the IC-910H)
  - Adding support for FT-8xx radios. Same approch: serial driver, although that will add additonal reworks in the doppler tracking loop to account for two radios
  - Building a much nicer GUI
  - Separate GUI and tracking class
  - Refactor tracking loop:
    - no global F0/I0 variables, more abstracted methods to allow eaier implementation of other radios
