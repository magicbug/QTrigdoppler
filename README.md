# QT RigDoppler


<picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
 <source media="(prefers-color-scheme: light)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
 <img alt="Shows QTRigDoppler GUI." src="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
</picture> 

## RigDoppler features doppler shift control for ICOM radios.

Based on K8DP Doug Papay rigdoppler (@K8DP_Doug)  
Adapted v0.3 and QT by EA4HCF Pedro Cabrera (@PCabreraCamara)  
Extended and modified to v0.4 by DL3JOP Joshua Petry (@dl3jop)

Attention: I'm looking for bug reports and new features. Every pull-request/issue is welcomed

## Requirements:  
    1) Python3  
    2) Required Python3 modules
       pip3 install ephem
       pip3 install PyQt5
       pip3 install urllib3
       pip3 install pyserial
    3) Python3 modules if you'd like to use the map:
       pip3 install matplotlib
       pip3 install cartopy
       pip3 install pyproj
  
## Support files:  

    1) TLE ephemerides file. (Example: https://tle.oscarwatch.org/)   
    2) doppler.sqf (included, mostly compatible to SatPC32)

## Changelog
v0.4 vs v0.3 and earlier (DL3JOP modifications):
    1) Removed hamlib
    2) support for IC-910H by direct serial communication, IC-9700 should work as well (not yet tested)
    3) Implemented transponder selection
    4) Implemented correct switch between Split mode for V/V & U/U packet and satmode for V/U,U/V
    5) Implemented doppler correction threshold
    6) Added SubTone control
    7) Various smaller changes and additions
    
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



## Roadmap:
  - Adding support for IC-9700 (should be easy as it uses nearly the same comands as the IC-910H)
  - Adding support for FT-8xx radios. Same approch: serial driver, although that will add additonal reworks in the doppler tracking loop to account for two radios
  - Building a much nicer GUI
  - Separate GUI and tracking class
  - Refactor tracking loop:
    - no global F0/I0 variables, more abstracted methods to allow eaier implementation of other radios
