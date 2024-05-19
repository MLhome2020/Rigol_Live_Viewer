'''
Autor:  MLHome2020
Date:   18.05.2024

Descr.: Simple PySide6 Live Viewer of a connected Rigol DS2072 Oscilloscope.
        This was just a prove of concept.

Rigol Live View
├── README
├── Rigol_Live_View.py  Start Script for the QApplication

Version:    V1.0

Change Notes:
2024-18-05      V1.0    First prototype Viewer
'''

import pyvisa           #pip install pyvisa
import time
import numpy as np
import sys
import io
from PIL import Image
import lecroyparser



from PySide6.QtWidgets  import (QApplication,QMainWindow,QInputDialog,QComboBox,QLabel,
                               QSizePolicy,QLineEdit,QGraphicsView,QGraphicsScene,QPushButton, 
                               QDialogButtonBox, QStyle, QWidget, QFileDialog, QStatusBar,
                                QFileDialog,QTreeWidgetItemIterator,QMenu, QToolBar, QDialog, QTableWidget, 
                                QTableWidgetItem, QVBoxLayout)

from PySide6.QtGui      import (QAction, QIcon, QDesktopServices, QFont, QColor,QClipboard,
                                QImage,QPixmap)

from PySide6.QtCore     import (QByteArray,QTimer,QIODevice,QFile,QObject,QThread,QSettings, 
                                QPoint, QRect, Qt, QUrl, QSize, QThreadPool, QRunnable,
                                Signal,Slot)

#For realtime graph we use pyqtgraph
import pyqtgraph as pg
from pyqtgraph import AxisItem
import lecroyparser


class ImageDialog(QDialog):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("Image Viewer")
        #self.setModal(True)  # Set the dialog to be modal
        
        layout = QVBoxLayout()

        image_label = QLabel()
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print("Error loading image:", image_path)
        else:
            # Scale the pixmap by 1.5 times
            #scaled_pixmap = pixmap
            scaled_pixmap = pixmap.scaled(pixmap.width() * 2, pixmap.height() * 2)
            image_label.setPixmap(scaled_pixmap)
            layout.addWidget(image_label)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)  # Close the dialog when OK is clicked
        layout.addWidget(ok_button)

        self.setLayout(layout)

#we use a similar Data structure as used by lecroyparser
class ScopeData_nativ():
    def __init__(self):
        self.path = "--"
        self.x = []
        self.y = []
        self.commOrder = ""
        self.endianness = "<"
        self.instrumentName = "Native"
        self.nominalBits = "8"
        self.instrumentNumber = 1
        self.templateName =""
        self.waveSource = ""
        self.waveArrayCount = 1
        self.verticalCoupling = ""
        self.verticalGain = 1
        self.verticalOffset = 0
        self.vertUnit = ""
        self.bandwidthLimit = ""
        self.recordType  = ""
        self.processingDone = ""
        self.timeBase = ""
        self.triggerTime = ""
        self.horizInterval = 1
        self.horizOffset = 0
        self.zerocross = 0.0


    def __repr__(self):
        string = f"Scope Data {self.waveSource}\n"
        string += "  Path: " + self.path + "\n"
        string += "  Endianness: " + self.endianness + "\n"
        string += "  Instrument: " + self.instrumentName + "\n"
        string += "  Instrument Number: " + str(self.instrumentNumber) + "\n"
        string += "  Template Name: " + self.templateName + "\n"
        string += "  Channel: " + self.waveSource + "\n"
        string += "  WaveArrayCount: " + str(self.waveArrayCount) + "\n"
        string += "  Vertical Coupling: " + self.verticalCoupling + "\n"
        string += "  verticalGain: " + str(self.verticalGain) + "/div \n"
        string += "  verticalOffset: " + str(self.verticalOffset) + "\n"
        string += "  vertUnit: " + self.vertUnit + "\n"
        string += "  Bandwidth Limit: " + self.bandwidthLimit + "\n"
        string += "  Record Type: " + self.recordType + "\n"
        string += "  Processing: " + self.processingDone + "\n"
        string += "  TimeBase: " + self.timeBase + "\n"
        string += "  TriggerTime: " + self.triggerTime + "\n"
        string += "  NominalBits: " + str(self.nominalBits) + "\n"
        string += "  HorizInterval: " + str(self.horizInterval) + "\n"
        string += "  horizOffset: " + str(self.horizOffset) + "\n"
        
        return string

class Rigol_get_Data(QThread):
    finished = Signal()
    data_receivedCH1 = Signal(ScopeData_nativ)
    data_receivedCH2 = Signal(ScopeData_nativ)
    Statustext = Signal(str)
   

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.scope = None
        self.rm = None
        self.stop_connection = False
        self.Livedata = False
        self.Scope_wave = {}

    def run(self):
        # Simulate some intensive computation
        while self._is_running:
            while self.scope is not None:
                if self.Livedata:
                    self.getData_online()
                    #print("Receiving data...")
                    self.data_receivedCH1.emit(self.Scope_wave['CHAN1'])
                    self.data_receivedCH2.emit(self.Scope_wave['CHAN2'])
                    #self.emit_status("Receiving data...")  # Emit status message

                #print("Emited.")
                if self.stop_connection == True:
                    self.scope.close()    
                    # Optionally, you can close the resource manager
                    self.rm.close()
                    self.scope = None
                time.sleep(0.25)
       
            self.emit_status("Disconnected")  # Emit status message
            time.sleep(0.25)
            
        self.finished.emit()

    def stop(self):
        self.disconnect_scope()
        self._is_running = False

    def emit_status(self, message):
        self.Statustext.emit(message)  # Emit the Statustext signal with a message

    def disconnect_scope(self):
        self.stop_connection = True
        
    def connect_scope_ADR(self,ADR):
        self.rm = pyvisa.ResourceManager()
        try:
            self.scope = self.rm.open_resource(ADR, timeout=12000)  #chunk_size=20*1024,write_termination = '\n', read_termination = '\n',
            self.stop_connection = False
            print(f"Successfull connected by PyVISA with {ADR}")
            return self.scope
        except pyvisa.VisaIOError:
            print("Connect fail!")
            return None
   
    def take_screenshot(self):
        if self.scope is not None:
            file_name = "New_Screen.bmp"
            #self.scope.write(":DISP:DATA?")
            #bmpdata = self.scope.query_binary_values(':DISP:DATA? ON,0,PNG', datatype='B')
            bmp_bin = self.scope.query_binary_values(':DISP:DATA?', datatype='B', container=bytes)
            #bmpdata = self.scope.read_raw()[2+9:]
            img = Image.open(io.BytesIO(bmp_bin))
            img.save(file_name)
            self.emit_status(f"Screenshot captured saved to {file_name}")  # Emit status message


    def getData_online(self):
        channels = ['CHAN1','CHAN2']
          
        for channel in channels:
            if not channel in self.Scope_wave :
                self.Scope_wave[channel] = ScopeData_nativ()
                self.Scope_wave[channel].x=[0,1]
                self.Scope_wave[channel].y=[0,0]
            #print(channel)
            all_data = bytearray()

            datapoints = 1400
            
            start_time = time.time()
          
            #self.Rigol_ESR(scope)
            self.scope.write(f':WAV:FORM BYTE')
            self.scope.write(f':WAV:SOUR {channel}')
            self.scope.write(f':WAV:MODE NORM')
           
            all_data = self.scope.query_binary_values(":WAV:DATA?", datatype='B',is_big_endian=True)
            
            # Query waveform parameters
            x_increment = self.scope.query_ascii_values(':WAV:XINC?', converter='f')[0]
            x_origin    = self.scope.query_ascii_values(':WAV:XOR?', converter='f')[0]
            y_increment = self.scope.query_ascii_values(':WAV:YINC?', converter='f')[0]
            y_origin    = self.scope.query_ascii_values(':WAV:YOR?', converter='f')[0]
            

            Probe       = self.scope.query_ascii_values(f':{channel}:PROB?', converter='f')[0]
            vcoupling   = self.scope.query_ascii_values(f':{channel}:COUPling?', converter='s')[0].strip()
            voffset     = self.scope.query_ascii_values(f':{channel}:OFFSet?', converter='f')[0]
            vscale      = self.scope.query_ascii_values(f':{channel}:SCALe?', converter='f')[0]
            BWlimit     = self.scope.query_ascii_values(f':{channel}:BWLimit?', converter='s')[0].strip()
            vUnits      = self.scope.query_ascii_values(f':{channel}:UNITs?', converter='s')[0].strip()
            
            self.Scope_wave[channel].waveSource =  channel
            self.Scope_wave[channel].waveArrayCount = len(all_data)
            self.Scope_wave[channel].horizInterval = x_increment
            self.Scope_wave[channel].horUnit = "s"
            self.Scope_wave[channel].horizOffset = x_origin
            self.Scope_wave[channel].path = "--"
            self.Scope_wave[channel].verticalCoupling = vcoupling
            self.Scope_wave[channel].verticalOffset = voffset
            self.Scope_wave[channel].verticalGain = vscale
            self.Scope_wave[channel].bandwidthLimit = BWlimit
            self.Scope_wave[channel].vertUnit = vUnits
            
            # Create time and
            time_array = np.arange(len(all_data)) * x_increment + x_origin
            
            # Asolut voltage
            #voltage_array = ((np.array(all_data) - 128) * 10 * vscale / 256)  + y_increment
            
            # Absolt Voltage but with y_origin acc oscilloscope screen
            #voltage_array = y_origin + ((np.array(all_data) - 128) * 10 * vscale / 256 - voffset + y_increment) # Old Firmware
            voltage_array = (((np.array(all_data) - 128) * 10 * vscale / 256 ) - voffset ) # - voffset + y_increment Old Firmware
            
            self.Scope_wave[channel].x = time_array
            self.Scope_wave[channel].y = voltage_array

            self.emit_status(f"{(time.time() - start_time):.2f}s Normal Read CH:{channel} {len(all_data)} points")  # Emit status message
            
        print(print(self.Scope_wave['CHAN1']))
        print(print(self.Scope_wave['CHAN2']))
        return True
    

class Rigol_Live(QMainWindow):
    closed = Signal()


    def __init__(self):
        super().__init__()
        self.scope = None
        self.LiveG_win = None
        self.plotitem  = None
        self.plotdataitem = None
        self.Scope_wave = {}
        self.ScreenViewer = None
        self.plot_abs = True
        
        self.resize(1000, 600)

        # Create menu bar
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('File')
        toolMenu = menubar.addMenu('Tool')

        # Create an exit action for the Exit menu
        exit_action_menu = QAction(QIcon(None), 'Exit', self)
        exit_action_menu.setShortcut('Ctrl+E')
        exit_action_menu.setStatusTip('Exit application')
        exit_action_menu.triggered.connect(self.close)
        # Add the exit action to the exit menu
        fileMenu.addAction(exit_action_menu)

        # Add actions to Tool menu
        connectAction = QAction(QIcon(), 'Connect', self)
        connectAction.triggered.connect(self.connect_tool)
        toolMenu.addAction(connectAction)

        DisconnectAction = QAction(QIcon(), 'DisConnect', self)
        DisconnectAction.triggered.connect(self.Disconnect_tool)
        toolMenu.addAction(DisconnectAction)


        self.connection_combo = QComboBox(self)
        self.connection_combo.addItems([
            "TCPIP0::192.168.1.30::inst0::INSTR",
            "TCPIP0::192.168.1.30::5555::SOCKET",
            "USB0::0x1AB1::0x04B0::DS2A153502286::INSTR"
        ])
        self.connection_combo.setEditable(True)
        self.connection_combo.setInsertPolicy(QComboBox.NoInsert)
        self.statusBar().addPermanentWidget(self.connection_combo)

        # Create a Screenshot button
        self.btn_screenshot = QPushButton("Screenshot", self)
        # Connect the button's clicked signal to a slot
        self.btn_screenshot.clicked.connect(self.initiate_screenshot)
        self.statusBar().addPermanentWidget(self.btn_screenshot)

        # Create a Display switch button to have absolute display or with offset acc scope 
        self.btn_absolut = QPushButton("Absolut", self)
        self.btn_absolut.setCheckable(True)
        self.btn_absolut.setChecked(True)
        # Connect the button's clicked signal to a slot
        self.btn_absolut.clicked.connect(self.plot_Absolut)
        self.statusBar().addPermanentWidget(self.btn_absolut)

        add_connection_action = QAction(QIcon(), 'Add Connection', self)
        add_connection_action.triggered.connect(self.add_connection_string)
        toolMenu.addAction(add_connection_action)


        #check if a pyqtgraph already has been cretaed if not create one QWindow
        #if self.LiveG_win is None:
        #    #self.LiveG = QApplication([])
        #    self.LiveG_win = pg.GraphicsLayoutWidget()
        #    self.setCentralWidget(self.LiveG_win)
        #    self.plotitem = self.LiveG_win.addPlot(title="PyQtGraph Test") 
        #    pg.setConfigOptions(antialias=True,useOpenGL=True)
        #    self.LiveG_win.resize(self.size())  # Resize LiveG_win to match QMainWindow size
        
        # Create and start the thread
        self.thread = QThread()
        self.Rigol_thread = Rigol_get_Data()
        self.Rigol_thread.moveToThread(self.thread)
        self.Rigol_thread.finished.connect(self.on_worker_finished)
        self.Rigol_thread.data_receivedCH1.connect(self.receive_dataCH1)
        self.Rigol_thread.data_receivedCH2.connect(self.receive_dataCH2)
        self.Rigol_thread.Statustext.connect(self.update_status)  # Connect the Statustext signal
        self.Rigol_thread.start()
        #Try to connect with first connection 
        self.connect_tool()

    def plot_Absolut(self,checked):
        print(checked)
        if checked:
            self.plot_abs = True
        else:
            self.plot_abs = False

    def initiate_screenshot(self):
        #self.Disconnect_tool()
        #connection_string = self.connection_combo.currentText()
        self.statusBar().showMessage(f'Get screenshot',3000)
        #self.Rigol_thread.connect_scope_ADR(connection_string)
        self.Rigol_thread.Livedata = False
        time.sleep(0.35)
        
        self.Rigol_thread.take_screenshot()

        self.statusBar().showMessage(f'Get screenshot captured',3000)
        self.Rigol_thread.Livedata = True

        #Show the image
        image_path = "New_Screen.png"
        self.ScreenViewer = ImageDialog(image_path)
        self.ScreenViewer.show()


    def add_connection_string(self):
        text, ok = QInputDialog.getText(self, 'Add Connection String', 'Enter new connection string:')
        if ok and text:
            self.connection_combo.addItem(text)

    def connect_tool(self):
        connection_string = self.connection_combo.currentText()
        self.statusBar().showMessage(f'Connecting to {connection_string}',5000)
        self.Rigol_thread.connect_scope_ADR(connection_string)
        self.Rigol_thread.Livedata = True

        self.pqTimer = QTimer()
        self.pqTimer.timeout.connect(self.plot_channel)
        self.pqTimer.start(500)  # 500 milliseconds
    

    def Disconnect_tool(self):
        print("Disconnect")
        self.Rigol_thread.disconnect_scope()
        self.statusBar().showMessage(f'Disconnected.')

   

    @Slot()
    def on_worker_finished(self):
        print("Worker thread finished")
        pass

    @Slot(str)
    def update_status(self, message):
        self.statusBar().showMessage(message, 2000)

    @Slot(ScopeData_nativ)
    def receive_dataCH1(self, data):
        #print("Update CH1", len(data.x))
        self.Scope_wave['CHAN1'] = data

    @Slot(ScopeData_nativ)
    def receive_dataCH2(self, data):
        #print("Updat CH2", len(data.x))
        self.Scope_wave['CHAN2'] = data
        #self.plot_channel()

    @Slot()
    def update_label(self):
        #print("update")
        pass


    def plot_channel(self):
        if "CHAN1" in self.Scope_wave and "CHAN2" in self.Scope_wave:
            max_x = np.max(self.Scope_wave['CHAN1'].x)
            min_x = np.min(self.Scope_wave['CHAN1'].x)
            max_x_last = max_x
            min_x_last = min_x

            voffset_CH1 = self.Scope_wave['CHAN1'].verticalOffset
            voffset_CH2 = self.Scope_wave['CHAN2'].verticalOffset
            x = self.Scope_wave['CHAN1'].x  
            if self.plot_abs:
                y1 = self.Scope_wave['CHAN1'].y    
                y2 = self.Scope_wave['CHAN2'].y  
            else:
                y1 = self.Scope_wave['CHAN1'].y + voffset_CH1 
                y2 = self.Scope_wave['CHAN2'].y + voffset_CH2 


            if self.LiveG_win is None:

                self.LiveG_win = pg.GraphicsLayoutWidget()
                self.setCentralWidget(self.LiveG_win)
                self.LiveG_win.resize(self.size())  # Resize LiveG_win to match QMainWindow size

 
                self.plotitem = self.LiveG_win.addPlot(title="PyQtGraph Test") 
                pg.setConfigOptions(antialias=True,useOpenGL=True)
                # Show grid
                self.plotitem.showGrid(x=True, y=True, alpha=0.5)


                
                # Initialize the plot items
                self.plotdataitem = self.plotitem.plot(x=x, y=y1, pen='y'  ) 
                self.plotdataitem1 = self.plotitem.plot(x=x, y=y2,  pen='c') 
                self.plotitem.setXRange(min_x, max_x)
               
                self.plotitem.showAxis('bottom')
                axB = self.plotitem.getAxis('bottom')
                axB.setLabel('Time', color='red',units='s')       #,units='s'
                
                self.plotitem.showAxis('left')
                axL = self.plotitem.getAxis('left')
               
                axL.setLabel('CHAN1', color='y',units='V',alpha=1)           # units='V'
                
                self.plotitem.showAxis('right')
                axR = self.plotitem.getAxis('right')
                axR.setLabel('CHAN2', color='c')            # units='V'
          
                self.plotitem.setYRange(-10, 10)
                self.plotitem.setYRange(min(y1), max(y1))
                
                # Show grid for both axes
                self.plotitem.showGrid(x=True, y=True, alpha=0.3)

                self.LiveG_win.raise_()
                self.LiveG_win.show()
            else:
                if max_x != max_x_last or min_x != min_x_last:
                    max_x_last = max_x
                    min_x_last = min_x
                    self.plotitem.setXRange(min_x, max_x)

                #update x range to see full range only if the 
                if max_x != max_x_last or min_x != min_x_last:
                    max_x_last = max_x
                    min_x_last = min_x
                    self.plotitem.setXRange(min_x, max_x)
                
                self.plotitem.setTitle(f"PyQtGraph Test {len(self.Scope_wave['CHAN1'].x)}")
                self.plotdataitem.setData(x=x, y=y1)
                self.plotdataitem1.setData(x=x, y=y2)

                
        else:
            print("NoDATA")


    def wait_ready(self,instrument):
        #instrument.write("*OPC")
        instrument.write("*WAI")
        ready = instrument.query("*OPC?").strip()
        #print(ready)
        while ready != "1":							# never occured, needed?
            ready = instrument.query("*OPC?").strip()
            print(f"\n-------------------not ready: {ready}-----------------------")
            #pass

    def Rigol_ESR(self,scope):
            # Query the current value of the Event Status Register ESR for the standard event register set.
            response = int(scope.query("*ESR?"))
            # Interpret the response and print the state of each bit
        
            bit_weights = [128, 64, 32, 16, 8, 4, 2, 1]
            bit_names = ["PON", "URQ", "CME", "EXE", "DDE", "QYE", "RQL", "OPC"]
            bit_long_names = ["Power On", "User Request", "Command Error", "Execution Error", "Dev. Dependent Error", "Query Error", "Request Control", "Operation Complete"]
            bit_states = [(response & bit_weights[i]) != 0 for i in range(8)]  # True if bit is enabled, False otherwise
            bit_info = dict(zip(bit_names, zip(bit_long_names, bit_states)))
        
            # Print the state of each bit
            print("Bit Name                 | Long Name            | State")
            print("-" * 60)  # Print a line separator
            for bit_name, (bit_long_name, bit_state) in bit_info.items():
                print(f"{bit_name.ljust(24)} | {bit_long_name.ljust(20)} | {bit_state}")
            scope_error = scope.query(":SYSTem:ERRor?")
            print(f"Error Text: {scope_error}")
            #Clear Errors
            scope.write('*CLS')

    def crange(self,start,end,step):
        i = start
        while i < end-step+1:
            yield i, i+step-1
            i += step
        yield i, end

    def closeEvent(self, event):
        self.on_exit(event)

    def on_exit(self,event):
        # Stop the worker thread
        self.Rigol_thread.stop()
        
        # Wait for the thread to finish
        self.thread.wait()
        
        # Accept the close event
        event.accept()
        
        # Emit the closed signal if needed
        self.closed.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    Rigol_View = Rigol_Live()
    Rigol_View.show()
   
    sys.exit(app.exec())  # Start the application event loop
    
    
