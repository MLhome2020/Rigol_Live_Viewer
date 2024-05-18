# Rigol_Live_Viewer

## Description
This project is a simple live viewer for a connected Rigol DS2072 Oscilloscope, implemented using PySide6 and PyQtGraph. The primary objective was to demonstrate the concept, with a target device of a LeCroy oscilloscope in mind.

![Screenshot of the application.](docs/Main%20Screen.JPG)


## Contents
README.md: This readme file.
Rigol_Live_View.py: The main script to start the PySide6 application.
Version
V1.0 - Initial prototype viewer

## Change Notes
2024-05-18: V1.0 - First prototype viewer

## Requirements
- Python 3.x
- PySide6
- PyQtGraph
- PyVISA

## Installation

Install the required packages using pip:
```
pip install pyvisa PySide6 pyqtgraph
```

## Usage
To start the application, run the Rigol_Live_View.py script:

## Code kopieren
'''
python Rigol_Live_View.py
'''

## Overview of Components

1. ScopeData_nativ
A class to store oscilloscope data. This class includes attributes such as path, x and y data points, instrument details, and wave parameters.

2. Rigol_get_Data
A QThread-based class to handle data retrieval from the oscilloscope. It emits signals when data is received and handles the connection and disconnection of the oscilloscope.

3. Rigol_Live
A QMainWindow-based class that sets up the GUI using PySide6. It includes a menu bar, status bar, and a central widget for displaying live graph data using PyQtGraph. It manages oscilloscope connection, disconnection, and real-time data plotting.

## GUI Components
Menu Bar: Contains 'File' and 'Tool' menus with actions to connect, disconnect, and exit.

Status Bar: Displays the current status of the connection and provides a combo box to select the connection string.

Graphics View: Utilizes PyQtGraph to display real-time data from the oscilloscope.

## Key Functions
### Rigol_get_Data

run(): Main loop to continuously fetch data from the oscilloscope.

connect_scope_ADR(ADR): Connects to the oscilloscope using the provided VISA address.

getData_online(): Fetches waveform data from the oscilloscope.

Disconnect_scope(): Stops the connection and closes the resource manager.

### Rigol_Live

connect_tool(): Initiates the connection to the oscilloscope.

Disconnect_tool(): Disconnects the oscilloscope.

plot_channel(): Updates the graph with new data.

receive_dataCH1(data), receive_dataCH2(data): Slots to receive and handle data signals for channels 1 and 2.

## Notes
The application was initially tested with a Rigol DS2072 oscilloscope. The final target device is a LeCroy oscilloscope.
The project is a proof of concept and may require adjustments for different oscilloscope models or additional features as needed.

## License
This project is developed by MLHome2020.

### Example Output
An example of the live view display using PyQtGraph:


## Troubleshooting
If you encounter issues with the connection:

Ensure the oscilloscope is connected by ethernet cable or USB and powered on.
Verify the VISA address and connection string is correct.

Check if the required packages are installed correctly.

## Contribution
Feel free to contribute by opening issues or submitting pull requests. For major changes, please open an issue first to discuss what you would like to change.

## Acknowledgements
PyVISA for handling the communication with the oscilloscope.
PySide6 for creating the GUI.
PyQtGraph for providing real-time plotting capabilities.
pylecroyparser for inspiration to do this examples
