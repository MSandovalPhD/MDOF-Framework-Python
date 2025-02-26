# Multiple Degrees-Of-Freedom Input Devices for Interactive Command and Control within Virtual Reality in Industrial Visualisations
LISU (which stands for Layered Interaction System for User-Modes) is a framework developed for managing the raw input data from heterogeneous input devices. LISU offers a solution for VR (Virtual Reality) developers, creators, and designers to resolve interoperability and compatibility issues in VR applications caused by the heterogeneity of input controllers by unifying the roles of multiple code segments and APIs for input management.

# Steps to reproduce
1. Open your terminal (in my case, I used PowerShell), and execute conda activate "NAME_OF_YOUR_ENVIRONMENT". 
2. Go to your root folder (or where you have downloaded the root folder "demo (version 3_0)".
3. Run the test file included, e.g., python .\Test_LisuGamepad.py (note: check that your device is in the ontology that is included in the folder Data/idoo.owl)

In addition:
To run Vrpn:
1. Run vrpn_server.exe from the Vrpn folder
2. Run the test file included in the folder "demo (version 3_0)", e.g., Test_VrpnGamepad.py

Note:
- All the work was conducted on a PC within Windows 10 Pro, Dell Optiplex 7010, with an Intel Core i7-3770S processor, clocked at 3.10 GHz. 
- The padlock mechanism CT datasets were provided by the Manchester X-ray Imaging Facility (http://www.mxif.manchester.ac.uk/). 
- The Ketton carbonate core CT datasets were obtained from the British Geological Survey (BGS) database (https://metadata.bgs.ac.uk/geonetwork/srv/api/records/7315b790-333e-4e5b-e054-002128a47908/).
- The Submillimetre mechanistic designs of termite-built structures CT datasets were obtained from Zenodo database (https://zenodo.org/record/4792633).
- Programming was done in Python (v.3.3), linking to the API of ANU Drishti version 2.6.4, compiled on Windows 10 using Qt 5.4.1 and libQGLViewer 2.6.1. 
- Controller setups were selected to be cross-evaluated; an Oculus Go Standalone Virtual Reality Headset - 32 GB, a SpeedLink SL-6638 Phantom Hawk Flightstick joystick, a Worthington Sharpe's Wing V.2, a Microsoft Xbox 360 controller, a Sony PS4 DualShock 4 V2 Wireless Controller, a custom setup consisting of a Keyboard + Mouse, and two 3DConnexion SpaceNavigators. 
