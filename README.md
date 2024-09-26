# QT RigDoppler v0.3 (stable release for Icom 705 and 9700)

Based on K8DP Doug Papay rigdoppler (@K8DP_Doug)  
Adapted v0.3 and QT by EA4HCF Pedro Cabrera (@PCabreraCamara)  
  
RigDoppler is a very simple Python3 script to correct doppler effect in radio satellites using Icom rigs connected to a computer.
<picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
 <source media="(prefers-color-scheme: light)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
 <img alt="Shows QTRigDoppler GUI." src="https://github.com/dl3jop/QTrigdoppler/blob/main/images/mainWindow.png">
</picture>  
  
## Requeriments:  
    1) Python3  
    2) Python3 modules
       pip3 install ephem
       pip3 install PyQt5
       pip3 install urllib3
    3) HamLib (https://hamlib.github.io/)  
  
Support files and download links:  

    1) TLE ephemerides file. (Exmple: https://www.pe0sat.vgnet.nl/satellite/tle/)   
    2) AmsatNames.txt (https://www.ea5wa.com/satpc32/archivos-auxiliares-de-satpc32)   
    3) dopler.sqf (https://www.ea5wa.com/satpc32/archivos-auxiliares-de-satpc32)  

  
AmsatNames.txt and dopler.sqf are wide and well known files used by PCSat32 software, so can be reused in the same computer.  

## v0.3 Limitations:
    1) Hamlib and/or CV-I commands tested on Icom 9700, 705 and Yaesu 818 radios.
    ### v0.3 ToDo List:
    1) Improve error handling, detect and correct bugs. 
    2) Solve the limitations.
    3) Let me know if you have something else in mind.
    
## Basic Configuration:
<picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
 <source media="(prefers-color-scheme: light)" srcset="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
 <img alt="Shows the GUI for editing config." src="https://github.com/dl3jop/QTrigdoppler/blob/main/images/menu_config.png">
</picture>  
    1) "Setup" menu, "Edit setup" item to review and change the parameters:. QTH Parameters
    
    - Latitude, Longitude and altitude.
    - Step for RX and TX offset sliders (Hertz units).
    - Maximun and minimun values for RX and TX offset sliders (Hertz units).

    Satellite parameters:
    Support files used to get satellites frequencies and ephemerides:

    - tle_file must contains ephemerides two line elements to calculate satellite passes over the coordinates in the [qth] section.
    - sqffile must contains satellites' frequencies (both downlink and uplink), following the same format as the original PCSat32 file.
    - amsatnames is just an auxiliary file son NORAD_ID satellites identifiers could be correlated with common satellites names used in doppler.sf file. Three columns per each satellite will list NORAD_ID identifier and common satellite name.

    Radio Parameters:
    - Setup your radio: Icom 9700, 705 or Yaesu 818
    - In case of Icom radio, setup your radio CV-I address

    Hamlib parameters:
    - IP address and TCP port used for communicate with "rigctl" daemon

    Offset Profiles:
    - Offsets will be automatically loaded when selecting the satellite. Format is the following:
        - Label "satoffset" followed by incremental number and the symbol "=", per each profile: satoffset1=, satoffset2=, satoffset3=, etc.
        - Satellite name, as found in doppler.sqf file, followed by ":" and
        - RX offset (Hertz) and TX offset, separated by comma ","

        Exmaple: satoffset1 = IO-117:-750,-750

  
## Execute script with Hamlib:  
    1) Open TCP connection from your computer to Icom rig using HamLib *rigctld* command:

      Unix/Linux:
      Icom 9700: rigctld -m 3081 -r /dev/YOUR_DEVICE -s 115200 -T 127.0.0.1
      Icom 705: rigctld -m 3085 -r /dev/YOUR_DEVICE -c 0xA4 -s 57600 -T 127.0.0.1
      Yaesu 818: rigctld -m 1041 -r /dev/YOUR_DEVICE -T 127.0.0.1

      Windows:
      Icom 9700: rigctld.exe -m 3081 -r COMx -s 115200 -T 127.0.0.1
      Icom 705: rigctld.exe -m 3085 -r COMx -c 0xA4 -s 57600 -T 127.0.0.1
      Yaesu 818: rigctld.exe -m 1041 -r COMx -T 127.0.0.1

    2) Check *config.ini* file and review all parameters, but really those are very important to review:  
        QTH coordinates: latitude, longitude and altitude 
        
    3) Execute RigDoppler: python3 /path/to/QTrigdoppler.py        
        
## Field Tests:

|     Radio     |   Satellite   |     Tester    |     Date    |
| ------------- | ------------- | ------------- | ----------- |
|  Icom 9700    |  GreenCube    |     EB1AO     |   Nov 23    |
|  Icom  705    |  GreenCube    |     EA4HCF    |   Nov 23    |

## GreenCube Operation with Icom 705

  1) Operate antenna untill receivinf the bursts in the 705 waterfall.
  2) Adjust RX offset until bursts should be centered in both the 705 waterfall and in the "soundmodem" waterfall, between 1000 and 2000 (only when the sallite is operating at 1200 bauds)
  3) Copy and paste the RX offset value from the RX input field to TX (both must be equal)
  4) Start transmitting and enjoy the melody

## Feedback and bug report

Yeah, that's life .. but I want to hear from you, so send an email or a tweet and I will answer you.

