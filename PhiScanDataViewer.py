import sys
import os
from numpy import double
import pandas as pd
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from pyqtgraph import PlotWidget, graphicsItems, TextItem
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem, PlotCurveItem

from PhiScanDataModel import *


class PolDataViewerWindow(QMainWindow):

    toggleVis = pyqtSignal()
    
    def __init__(self, configFile):
        super().__init__()
        self.initUI()
        self.analyser = Analyser()
        self.phi = None
        self.config_file = configFile
                    

    def closeEvent(self, event):

        """Shutdown event handling"""

        quit_msg = "Are you sure you want to exit the program?"
        reply = QMessageBox.question(self, 'Confirm shutdown', 
                        quit_msg, QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
            
            self.visTimer.stop()
        
        else:
            event.ignore()    

            
    def dragEnterEvent(self, event):

        """Drag event for file handling"""

        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()


    def dropEvent(self, event):

        """Drop event for file handling"""

        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if f not in self.analyser.files and f.endswith(".pkl"):
                self.analyser.files.append(f)
                print("Dataset added")
                self.updateTable()


    def updateTable(self):

        """Update table"""

        try:
            
            for i in range(len(self.analyser.files)):
                f = self.analyser.files[i]
                key = f.split('/')[-1].split(".pkl")[0].split("_")[0]
                
                self.lblStatus.setText("Status: Processing")
                self.analyser.dfDict[key] = pd.read_pickle(f)
                if key in ['Reference', 'ref', 'F1', 'F1_reference', 'F1_Reference', 'F1Ref', 'F1ref']:
                    #always select the last loaded reference as the global reference for future calculations
                    self.analyser.referenceDF = self.analyser.dfDict[key]
                    
                self.tableWidget.insertRow(i+ self.tableWidget.rowCount())
                self.lblStatus.setText("Status: Ready")
            for row in range(self.tableWidget.rowCount()):
                for col in range(self.tableWidget.columnCount()):
                    if col % 4 == 0:
                        item = QTableWidgetItem(f"{list(self.analyser.dfDict.keys())[row]}".format(row,col))
                        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                        item.setCheckState(Qt.CheckState.Unchecked)
                        self.tableWidget.setItem(row,col,item)
                    if col == 1:
                        # print("F1" not in list(self.analyser.dfDict.keys())[row])
                        if (('F1' not in list(self.analyser.dfDict.keys())[row])&('Reference' not in list(self.analyser.dfDict.keys())[row])&('reference' not in list(self.analyser.dfDict.keys())[row])):
                            item = QTableWidgetItem("Sample".format(row,col))
                        else:
                            item = QTableWidgetItem("Reference".format(row,col))
                        self.tableWidget.setItem(row,col,item)
            self.updatePlot()

        except Exception as e:
            print("invalid data format")
            raise e


    def initUI(self):

        """Initialise user interface"""

        uic.loadUi("PolDataViewerUI.ui", self)
        self.setWindowTitle("THEA PolDataViewer")
        
        self.initAttribs()
        self.connectEvents()
        self.livePlot.showGrid(x = True, y = True)
        self.labelValue = TextItem('', **{'color': '#FFF'})
        self.labelValue.setPos(QPointF(4,-100))
        self.livePlot.addItem(self.labelValue)

        self.comboBoxMeasurement.activated.emit(0)
        
        self.setAcceptDrops(True)
        self.tableWidget.width()
        self.tableWidget.setToolTip("Drag and drop .pkl PhiScan dataframes")
        tableHeader  = self.tableWidget.horizontalHeader()
        tableHeader.setSectionResizeMode(1,QHeaderView.ResizeToContents)

     
    def rescalePlot(self, x1,x2,px,y1,y2,py):
        
        """Sets the plot axes"""

        self.livePlot.setXRange(x1,x2, padding = px)
        self.livePlot.setYRange(y1, y2, padding = py)


    def initAttribs(self):

        """Initialise app attributes"""

        self.height = 650
        self.width = 1000
        self.left = 10
        self.top = 40      
        self.labelValue = None         #LabelItem to display timelapse frames on plot
        self.setGeometry(self.left, self.top, self.width, self.height)   
        self.colorLivePulse = (66,155,184, 145)
        self.colorlivePulseBackground = (66,155,184,145)
        self.livePlotLineWidth = 1
        self.averagePlotLineWidth = 1.5
        self.plotDataContainer = {}       # Dictionary for plot items

        
        self.visTimer = QTimer(self)
        self.visTimer.setInterval(500)
        self.visTimer.start()


    def connectEvents(self):

        """Event connections"""

        self.livePlot.scene().sigMouseMoved.connect(self.mouseMoved)
        self.lEditPhi.editingFinished.connect(self.validateEditPhi)
        self.comboBoxMeasurement.activated.connect(self.selectMeasurement)
        self.visTimer.timeout.connect(self.checkVisibilityFlags)
        # self.tableWidget.stateChanged.connect(self.updatePlot)

    
    def updatePlot(self):

        
        key = self.comboBoxMeasurement.currentText()
        if key != "TDS":
            xKey = 'freq' 
            yKey = key
        else:
            xKey = 'time'
            yKey = 'amp'
        
        self.plot(self.analyser.dfDict['F1'].loc[0][xKey],20*np.log(np.abs(self.analyser.dfDict['F1'].loc[0][yKey])))

    def checkVisibilityFlags(self):

        for row in range(self.tableWidget.rowCount()):
            if self.tableWidget.item(row, 0).checkState() == Qt.Checked:
                #print(f"Showing {self.tableWidget.item(row, 0).text()} data")
                pass
            if self.tableWidget.item(row, 0).checkState() == Qt.Unchecked:
                pass
                #print(f"{self.tableWidget.item(row, 0).text()} data hidden")


    def selectMeasurement(self):

        """Plot formatting for selected measurement"""

        if self.comboBoxMeasurement.currentIndex() == 0:
            print("FFT")
            self.rescalePlot(0,3.5,0,-250,-105,0)
            self.livePlot.setLabel('left', 'Transmission Intensity (dB)')
            self.livePlot.setLabel('bottom', 'Frequency (THz)')
            self.livePlot.setTitle("""Transmission FFT""", color = 'g', size = "45 pt")   

        elif self.comboBoxMeasurement.currentIndex() == 1:
            print("TR")
            self.rescalePlot(0,3.5,0,-10,10,0)
            self.livePlot.setLabel('left', 'Transmission Ratio')
            self.livePlot.setLabel('bottom', 'Frequency (THz)')
            self.livePlot.setTitle("""Transmission Ratio""", color = 'r', size = "45 pt")   
        elif self.comboBoxMeasurement.currentIndex() == 2:
            print("TDS")    
            self.rescalePlot(0,35,0,-2,2,0)        
            self.livePlot.setLabel('left', 'Signal (mV)')
            self.livePlot.setLabel('bottom', 'Time (ps)')
            self.livePlot.setTitle("""THz - TDS""", color = 'y', size = "45 pt")   
  

    def validateEditPhi(self):
        
        """
            Validate user input for Requested Frames of the timelapse
        """ 
        
        validationRule = QDoubleValidator(-120,120,3)
        print(validationRule.validate(self.lEditPhi.text(),120))
        if validationRule.validate(self.lEditPhi.text(),
                                   120)[0] == QValidator.Acceptable:
            print(f"Phi input ACCEPTED")
            
        else:
            print(f"> [WARNING]:Invalid angle.")
            
            self.phi =0
            self.lEditPhi.setText(str(self.phi))


    def plot(self, x, y):

        """
            Plot data on existing plot widget.
            :type x: numpy array
            :param x: frequency axis data
            :type y: numpy array
            :param y: Pulse FFT data.
            :return: plot data.
            :rtype: PlotWidget.plot  
        """   

        return self.livePlot.plot(x,y)

    
    def mouseMoved(self, evt):

        """
            Track mouse movement on data plot in plot units (arb.dB vs THz)
            :type evt: pyqtSignal 
            :param evt: Emitted when the mouse cursor moves over the scene. Contains scene cooridinates of the mouse cursor.
        """

        pos = evt
        if self.livePlot.sceneBoundingRect().contains(pos):
            mousePoint = self.livePlot.plotItem.vb.mapSceneToView(pos)
            x = float("{0:.3f}".format(mousePoint.x()))
            y = float("{0:.3f}".format(mousePoint.y()))
            self.xyLabel.setText(f"last cursor position: {x, y}")


if __name__ =="__main__":
    app = QApplication(sys.argv)
    win = PolDataViewerWindow('../config/polDataViewerConfig.yml')
    win.show()
    app.exec()
    