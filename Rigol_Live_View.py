'''
Autor:  MLHome2020
Date:   18.05.2024

Descr.: Simple PySide6 Live Viewer of a connected Rigol DS2072 Oscilloscope.
        This was just a prove of concept the target oscilloscope is a LeCroy

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

from PySide6.QtWidgets  import (QApplication,QMainWindow,QInputDialog,QComboBox,
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

#we use a similar Data structure as used by lecroyparser
class ScopeData_nativ():
    def __init__(self):
        self.path = ""
        self.x = []
        self.y = []
        self.endianness = "<"
        self.instrumentName = "Native"
        self.instrumentNumber = 1
        self.templateName =""
        self.waveSource = ""
        self.waveArrayCount = 1
        self.verticalCoupling = ""
        self.verticalGain = 1
        self.verticalOffset = 0
        self.bandwidthLimit = ""
        self.recordType  = ""
        self.processingDone = ""
        self.timeBase = ""
        self.vertUnit = ""
        
        self.triggerTime = ""
        self.horizInterval = 1
        self.horizOffset = 0
        self.zerocross = 0.0

        self.y = [] 
        self.x = [] 


class Rigol_get_Data(QThread):
    finished = Signal()
    data_receivedCH1 = Signal(ScopeData_nativ)
    data_receivedCH2 = Signal(ScopeData_nativ)
    Statustext = Signal(str)

    def __init__(self):
        super().__init__()
        self.scope = None
        self.rm = None
        self.stop_connection = False
        self.Scope_wave = {}

    def run(self):
        # Simulate some intensive computation
        while True:
            while self.scope is not None:
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

    def emit_status(self, message):
        self.Statustext.emit(message)  # Emit the Statustext signal with a message


    def Disconnect_scope(self):
        self.stop_connection = True
        
        
    def connect_scope_ADR(self,ADR):
        self.rm = pyvisa.ResourceManager()
        try:
            self.scope = self.rm.open_resource(ADR, timeout=10000 ,chunk_size=20*1024,write_termination = '\n', read_termination = '\n',)
            self.stop_connection = False
            print(f"Successfull connected by PyVISA with {ADR}")
            return self.scope
        except pyvisa.VisaIOError:
            print("Connect fail!")
            return None
   
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

            vscale      = self.scope.query_ascii_values(f':{channel}:SCALe?', converter='f')[0]
            voffset     = self.scope.query_ascii_values(f':{channel}:OFFSet?', converter='f')[0]
           
            # Create time and
            time_array = np.arange(len(all_data)) * x_increment + x_origin
            
            # Asolut voltage
            voltage_array = (np.array(all_data) - 128) * 10 * vscale / 256 - voffset + y_increment
            
            # Absolt Voltage but with y_origin acc oscilloscope screen
            voltage_array = y_origin + ((np.array(all_data) - 128) * 10 * vscale / 256 - voffset + y_increment)
            
            self.Scope_wave[channel].waveArrayCount = len(time_array)

            self.Scope_wave[channel].horizInterval = x_increment
            self.Scope_wave[channel].horUnit = "s"
            self.Scope_wave[channel].horizOffset = x_origin
            self.Scope_wave[channel].path = ""
            self.Scope_wave[channel].vertUnit = "V"
            
            self.Scope_wave[channel].x = time_array
            self.Scope_wave[channel].y = voltage_array
            self.emit_status(f"{(time.time() - start_time):.2f}s Normal Read CH:{channel} {len(all_data)} points")  # Emit status message
            
        #scope.close()
        return True
    

class Rigol_Live(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scope = None
        self.LiveG_win = None
        self.plotitem  = None
        self.plotdataitem = None
        self.Scope_wave = {}

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
            "TCPIP0::192.168.1.23::inst0::INSTR",
            "TCPIP0::192.168.1.23::5555::SOCKET",
            "USB0::0x1AB1::0x04B0::DS2A153502286::INSTR"
        ])
        self.connection_combo.setEditable(True)
        self.connection_combo.setInsertPolicy(QComboBox.NoInsert)
        self.statusBar().addPermanentWidget(self.connection_combo)

        add_connection_action = QAction(QIcon(), 'Add Connection', self)
        add_connection_action.triggered.connect(self.add_connection_string)
        toolMenu.addAction(add_connection_action)


        #check if a pyqtgraph already has been cretaed if not create one QWindow
        if self.LiveG_win is None:
            #self.LiveG = QApplication([])
            self.LiveG_win = pg.GraphicsLayoutWidget()
            self.setCentralWidget(self.LiveG_win)
            self.plotitem = self.LiveG_win.addPlot(title="PyQtGraph Test") 
            pg.setConfigOptions(antialias=True,useOpenGL=True)
            self.LiveG_win.resize(self.size())  # Resize LiveG_win to match QMainWindow size
            
        self.Rigol_thread = Rigol_get_Data()
        self.Rigol_thread.finished.connect(self.on_worker_finished)
        self.Rigol_thread.data_receivedCH1.connect(self.receive_dataCH1)
        self.Rigol_thread.data_receivedCH2.connect(self.receive_dataCH2)
        self.Rigol_thread.Statustext.connect(self.update_status)  # Connect the Statustext signal
        self.Rigol_thread.start()
        #Try to connect with first connection 
        self.connect_tool()

    
    def add_connection_string(self):
        text, ok = QInputDialog.getText(self, 'Add Connection String', 'Enter new connection string:')
        if ok and text:
            self.connection_combo.addItem(text)

    def connect_tool(self):
        connection_string = self.connection_combo.currentText()
        self.statusBar().showMessage(f'Connecting to {connection_string}',3000)
        self.Rigol_thread.connect_scope_ADR(connection_string)

        self.pqTimer = QTimer()
        self.pqTimer.timeout.connect(self.plot_channel)
        self.pqTimer.start(500)  # 500 milliseconds
    

    def Disconnect_tool(self):
        print("Disconnect")
        self.Rigol_thread.Disconnect_scope()
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
        #state =  self.getData_online()
        max_x = np.max(self.Scope_wave['CHAN1'].x)
        min_x = np.min(self.Scope_wave['CHAN1'].x)
        
        if "CHAN1" in self.Scope_wave:
            max_x_last = max_x
            min_x_last = min_x
            
            # (Optional) Add some data to the plots (replace with your data)
            x = self.Scope_wave['CHAN1'].x   #self.channels['CHAN1'].x
            y1 = self.Scope_wave['CHAN1'].y #self.channels['CHAN1'].y
            y2 = self.Scope_wave['CHAN2'].y #self.channels['CHAN2'].y

            #check if a pyqtgraph already has been cretaed if not create one QWindow
            if self.LiveG_win is None:
                self.LiveG_win = pg.GraphicsLayoutWidget()
                self.plotitem = self.LiveG_win.addPlot(title="PyQtGraph Test") 
                
                pg.setConfigOptions(antialias=True,useOpenGL=True)

            if self.plotdataitem is None:
                #Faster
                self.plotdataitem = self.plotitem.plot(x=x, y=y1, pen='y'  ) #, symbolBrush=(255,0,0), symbolSize=5, symbolPen=None)
                self.plotdataitem1 = self.plotitem.plot(x=x, y=y2,  pen='c') #, symbolBrush=(255,200,0), symbolSize=5, symbolPen=None)
                #Slower when we do width lines larger as 1
                #self.plotdataitem = self.plotitem.plot(x=x, y=y1, pen={'color': (200, 150, 0),'width':2}, symbol=None)
                #self.plotdataitem1 = self.plotitem.plot(x=x, y=y2, pen={'color': 'b', 'width': 2}, symbol=None)
                
                # Set X Range
                self.plotitem.setXRange(min_x, max_x)
                # Set Y Range for left axis
                self.plotitem.setYRange(-10, 10)

                # Add a second y-axis on the right
                self.plotitem.showAxis('right')
                self.plotitem.showAxis('bottom')

                num_samples = 1400
                custom_ticks = [(i, str(i)) for i in range(num_samples)]
    
                self.plotitem.getAxis('left').setLabel('CHAN1', color='y',units='V')
                self.plotitem.getAxis('left').linkToView(self.plotitem.getViewBox())
                self.plotitem.getAxis('right').setLabel('CHAN2', color='c',units='V')
                self.plotitem.getAxis('right').linkToView(self.plotitem.getViewBox())

                self.plotitem.getAxis('bottom').setLabel('Time', color='red',units='s')
                # Set Y Range for right axis (for y2 data)
                self.plotitem.getAxis('left').setRange(min(y1), max(y1))
                self.plotitem.getAxis('right').setRange(min(y2), max(y2))
                # Show grid for both axes
                self.plotitem.showGrid(x=True, y=True, alpha=1)

                self.LiveG_win.raise_()
                self.LiveG_win.show()
            else:
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

    def on_exit(self,ev):
        ev.accept()
        self.closed.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    Rigol_View = Rigol_Live()
    Rigol_View.show()
   
    sys.exit(app.exec())  # Start the application event loop
    
    