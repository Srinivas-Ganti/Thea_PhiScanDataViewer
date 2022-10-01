import sys
import os
from numpy import double
import pandas as pd
from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import QtSvg
from pyqtgraph import PlotWidget, graphicsItems, TextItem, mkPen
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem, PlotCurveItem
import pyqtgraph as pg
from matplotlib import cm


baseDir =  os.path.dirname(os.path.abspath(__file__))
sys.path.append(baseDir)

from PhiScanDataModel import *


class PolDataViewerWindow(QMainWindow):

    toggleVis = pyqtSignal(dict)
    water_peaks = [0.558, 0.752, 0.989, 1.098, 1.155, 1.164, 1.209, 1.229,\
               1.412, 1.604, 1.665, 1.718, 1.764, 1.798, 1.870, 1.921, \
               2.042, 2.076, 2.167, 2.197, 2.224, 2.265, 2.347, 2.367,\
               2.394, 2.464]


    def __init__(self, configFile):
        super().__init__()
        self.analyser = Analyser()
        self.initUI()
        
        self.phi = None
        self.config_file = configFile
        self.phi_idx = 0

        for i in range(len(self.water_peaks)):
            item = pg.InfiniteLine(pos = self.water_peaks[i],
                               pen = mkPen((100,100,0,180),
                               width=2, style=Qt.DashLine))
            self.waterLines.append(item)
        

    def closeEvent(self, event):

        """Shutdown event handling"""

        quit_msg = "Are you sure you want to exit the program?"
        reply = QMessageBox.question(self, 'Confirm shutdown', 
                        quit_msg, QMessageBox.Yes, QMessageBox.No)

        if reply == QMessageBox.Yes:
        
            self.visTimer.stop()
            self.animationTimer.stop()
        
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
        self.lblStatus.setText("Status: Processing")
        self.updateTable() 
        self.visTimer.start()
        self.animationTimer.start()
        

    def updateTable(self):

        """Update table"""

        try:
            # Load data
            self.lblStatus.setText("Status: Processing")
            phi_vals = np.linspace(90,-90,360)
            for i in range(len(self.analyser.files)):
                f = self.analyser.files[i]
                key = f.split('/')[-1].split(".pkl")[0].split("_")[0]
                
                self.lblStatus.setText("Status: Processing")
                self.analyser.dfDict[key] = pd.read_pickle(f)
                self.analyser.dfDict[key]['phi'] = phi_vals
                self.analyser.dfDict[key] = self.analyser.convDF(self.analyser.dfDict[key])
                
                if len(self.analyser.files) > self.tableWidget.rowCount():
                    self.tableWidget.insertRow(self.tableWidget.rowCount())
                    print("Row added", self.tableWidget.rowCount())
                #if key in ['Reference', 'ref', 'F1', 'F1_reference', 'F1_Reference', 'F1Ref', 'F1ref']:
                if ("Ref" in key) or ("ref" in key):
                    #always select the last loaded reference as the global reference for future calculations
                    self.analyser.referenceDF = self.analyser.dfDict[key]
              
                self.lblStatus.setText("Status: Ready")
                print("Data added")
            # Prepare plot colors
            if self.analyser.referenceDF is not None:
                for key in self.analyser.dfDict:
                    self.analyser.dfDict[key] = self.analyser.get_samples(self.analyser.dfDict[key], self.analyser.referenceDF)

            palette = cm.get_cmap('rainbow', len(self.analyser.dfDict))
            self.plotColors = palette(np.linspace(0,1,len(self.analyser.dfDict)))*255
            self.plotColors = np.around(self.plotColors)
         
            # Update table
            for row in range(len(self.analyser.files)):
               
                
                self.tableWidget.setItem(row,2,QTableWidgetItem())
                self.tableWidget.item(row,2).setBackground(QColor(int(self.plotColors[row][0]),int(self.plotColors[row][1]),int(self.plotColors[row][2])))
                
                for col in range(self.tableWidget.columnCount()):
                    if col % 3 == 0:
                        item = QTableWidgetItem(f"{list(self.analyser.dfDict.keys())[row]}".format(row,col))
                        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                        item.setCheckState(Qt.CheckState.Checked)
                        self.tableWidget.setItem(row,col,item)
                    if col == 1:
                        # print("F1" not in list(self.analyser.dfDict.keys())[row])
                        if (('Ref' not in list(self.analyser.dfDict.keys())[row])&('ref' not in list(self.analyser.dfDict.keys())[row])&('reference' not in list(self.analyser.dfDict.keys())[row])):
                            item = QTableWidgetItem("Sample".format(row,col))
                        else:
                            item = QTableWidgetItem("Reference".format(row,col))
                        self.tableWidget.setItem(row,col,item)
            self.plotData()

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
        self.plotLineWidth = 1.5
        self.livePlot.addItem(self.labelValue)

        self.comboBoxMeasurement.activated.emit(0)
    
        self.setAcceptDrops(True)
        self.tableWidget.width()
        self.tableWidget.setToolTip("Drag and drop .pkl PhiScan dataframes")
        tableHeader  = self.tableWidget.horizontalHeader()
        tableHeader.setSectionResizeMode(1,QHeaderView.ResizeToContents)
        self.lEditSpeed.setAlignment(Qt.AlignCenter) 
        self.lEditPhi.setAlignment(Qt.AlignCenter) 

        
        pixmap = QPixmap('drawing.png')
        self.graphicLabel.setPixmap(pixmap)
        self.graphicLabel.setScaledContents(True)
        self.graphicLabel.show()

       
     
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
        
        self.labelValue = TextItem('', **{'color': '#FFF'})
        self.labelValue.setPos(QPointF(4,-100))

        self.plotVisDict = {} # dictionary for visibility status
        self.visTimer = QTimer(self)
        self.visTimer.setInterval(20)
        self.animationTimer = QTimer(self)
        self.lEditSpeed.setText("25")
        self.lEditSpeed.editingFinished.emit()
        self.lEditPhi.setText("90")
        self.lEditPhi.editingFinished.emit()
        self.btnPlay.setCheckable(True)
        self.currentState, self.previousState = [{} for i in range(2)]
        self.lEditPhi.setReadOnly(True)
        self.waterLines = []


    def connectEvents(self):

        """Event connections"""

        self.livePlot.scene().sigMouseMoved.connect(self.mouseMoved)
        self.lEditPhi.editingFinished.connect(self.validateEditPhi)
        self.comboBoxMeasurement.activated.connect(self.selectMeasurement)
        self.lEditSpeed.editingFinished.connect(self.validateEditSpeed)
        self.checkBoxWaterLines.toggled.connect(self.toggleWaterLines)
        self.visTimer.timeout.connect(self.checkVisibilityFlags)
        self.animationTimer.timeout.connect(self.refreshPlot)
        self.btnPlay.clicked.connect(self.playScan)
        

    def toggleWaterLines(self):

        """Waterlines overlay toggle view"""

        waterLinesCopy = self.waterLines
            
        for i,waterline in enumerate(waterLinesCopy):
            if self.checkBoxWaterLines.isChecked():
                self.livePlot.addItem(waterLinesCopy[i])
            else:
                self.livePlot.removeItem(waterLinesCopy[i])


    def playScan(self):

        """Play/ Pause plot animation"""

        if self.btnPlay.isChecked():
            self.animationTimer.stop()
            self.lEditPhi.setReadOnly(False)
            self.lblStatus.setText("Status: Ready")
        else:
            self.animationTimer.start()
            self.lEditPhi.setReadOnly(True)
            self.lblStatus.setText("Status: Busy")


    def refreshPlot(self):

        """Update plot"""

        lblSceneX = self.livePlot.getViewBox().state['targetRange'][0][0] + np.abs(self.livePlot.getViewBox().state['targetRange'][0][1] - self.livePlot.getViewBox().state['targetRange'][0][0])*0.80
        lblSceneY =  self.livePlot.getViewBox().state['targetRange'][1][0] + np.abs(self.livePlot.getViewBox().state['targetRange'][1][1] - self.livePlot.getViewBox().state['targetRange'][1][0])*0.95
        self.labelValue.setPos(QPointF(lblSceneX,lblSceneY))
        self.lblStatus.setText("Status: Busy")
        if self.currentState:        
            self.phi_idx += 1
            
            if self.phi_idx == 359:
                self.phi_idx = 0
            ckey = self.comboBoxMeasurement.currentText()
            if ckey != "TDS":
                self.xKey = 'freq' 
                self.yKey = ckey
            else:
                self.xKey = 'time'
                self.yKey = 'amp'
            for key in self.plotVisDict:
                currentPhi = f"{self.analyser.dfDict[key].loc[self.phi_idx]['phi']:.2f}"    
                if ckey == 'FFT':

                    xData = self.analyser.dfDict[key].loc[self.phi_idx][self.xKey]
                    yData = 20*np.log(np.abs(self.analyser.dfDict[key].loc[self.phi_idx][self.yKey]))

                elif ckey == 'TDS':
                    
                    xData = self.analyser.dfDict[key].loc[self.phi_idx][self.xKey]
                    yData = self.analyser.dfDict[key].loc[self.phi_idx][self.yKey]

                elif ckey == 'TR' and self.analyser.referenceDF is not None:
                    
                    xData = self.analyser.dfDict[key].loc[self.phi_idx][self.xKey]
                    yData = self.analyser.dfDict[key].loc[self.phi_idx][self.yKey]

                self.setValues(key, xData, yData)
                self.labelValue.setText(f"""Data: {self.phi_idx}/360\nPhi: {currentPhi} deg""")
                self.lEditPhi.setText(f"{currentPhi}")
                

    def plotData(self):

        """Plot data, create curves"""

        ckey = self.comboBoxMeasurement.currentText()
        if ckey != "TDS":
            self.xKey = 'freq' 
            self.yKey = ckey
        else:
            self.xKey = 'time'
            self.yKey = 'amp'
        print("Looping through data dict")
        for k in range(len(self.analyser.dfDict)):
            key = list(self.analyser.dfDict.keys())[k]
            pen = mkPen(color = (self.plotColors[k]), width = self.plotLineWidth)
            if ckey == 'FFT':
                xData = self.analyser.dfDict[key].loc[self.phi_idx][self.xKey]
                yData = 20*np.log(np.abs(self.analyser.dfDict[key].loc[self.phi_idx][self.yKey]))
            elif ckey == 'TDS' or ckey == 'TR':
                
                xData = self.analyser.dfDict[key].loc[self.phi_idx][self.xKey]
                yData = self.analyser.dfDict[key].loc[self.phi_idx][self.yKey]
            print("Current key and plot item")
            print(key, self.plotVisDict)
            if key not in self.plotVisDict.keys():
                self.addCurve(key,pen)
                print("Curve Added")
                self.setValues(key, xData, yData)          
                self.currentState[key] = True
            self.previousState[key] = self.currentState[key]
          
            
    def addCurve(self, curve_id, pen):
        
        """Add curve"""

        plot = self.livePlot.plot(name=curve_id, pen=pen)
        self.plotVisDict[curve_id] = plot
        self.currentState[curve_id] = True
        self.previousState[curve_id] = False


    def removeCurve(self, curve_id):
        
        """Remove curve"""

        curve_id = str(curve_id)

        if curve_id in self.plotVisDict:
            self.livePlot.removeItem(self.plotVisDict[curve_id])
            
            self.livePlot.clear()
            self.currentState[curve_id] = False
            self.previousState[curve_id] = True
            self.plotVisDict.pop(curve_id, None)
            self.livePlot.show()


    def setValues(self, curve_id, xData, yData):

        """Set curve data"""

        curve = self.plotVisDict[curve_id]
        curve.setData(xData, yData)


    def checkVisibilityFlags(self):

        """Check table checkboxes to show/hide plot items"""

        if self.currentState:
            try:
                for row in range(self.tableWidget.rowCount()):
                    key = self.tableWidget.item(row, 0).text()
                    pen = mkPen(color = (self.plotColors[row]), width = self.plotLineWidth)
                    if (self.tableWidget.item(row, 0).checkState() == Qt.Checked) and key not in self.plotVisDict:
                            self.addCurve(key,pen)
                    if self.tableWidget.item(row, 0).checkState() == Qt.Unchecked and key in self.plotVisDict:
                        self.removeCurve(key)    
            except Exception as e:
                raise e
            

    def selectMeasurement(self):

        """Plot formatting for selected measurement"""

        if self.comboBoxMeasurement.currentIndex() == 0:
            print("FFT")
            self.rescalePlot(0.53,1.25,0,-170,-90,0)
            self.livePlot.setLabel('left', 'Transmission Intensity (dB)')
            self.livePlot.setLabel('bottom', 'Frequency (THz)')
            self.livePlot.setTitle("""Transmission FFT""", color = 'g', size = "45 pt")   

        elif self.comboBoxMeasurement.currentIndex() == 1:
            print("TR")
            self.rescalePlot(0.45,1.55,0,0.35,3,0)
            self.livePlot.setLabel('left', 'Transmission Ratio')
            self.livePlot.setLabel('bottom', 'Frequency (THz)')
            self.livePlot.setTitle("""Transmission Ratio""", color = 'r', size = "45 pt")   
        elif self.comboBoxMeasurement.currentIndex() == 2:
            print("TDS")    
            self.rescalePlot(10,50,0,-1.65,1.25,0)        
            self.livePlot.setLabel('left', 'Signal (mV)')
            self.livePlot.setLabel('bottom', 'Time (ps)')
            self.livePlot.setTitle("""THz - TDS""", color = 'y', size = "45 pt") 

        
    def validateEditSpeed(self):

        """Validate speed user input"""
                        
        validationRule = QIntValidator(1,60)
        
        if validationRule.validate(self.lEditSpeed.text(),
                                   60)[0] == QValidator.Acceptable:
            print("Speed input accepted")
            self.speed = round(1/int(self.lEditSpeed.text())*1000)
            self.animationTimer.stop()
            print(f"Speed = {self.speed}")
            self.animationTimer.setInterval(self.speed)
            self.animationTimer.start()
        else:
            print("Invalid speed Input")


    def validateEditPhi(self):
        
        """
            Validate user input for Requested Frames of the timelapse
        """ 
        
        validationRule = QDoubleValidator(-120,120,3)
        print(validationRule.validate(self.lEditPhi.text(),120))
        if validationRule.validate(self.lEditPhi.text(),
                                   120)[0] == QValidator.Acceptable:
            print(f"Phi input ACCEPTED")
            self.phi = float(self.lEditPhi.text())
        else:
            print(f"> [WARNING]:Invalid angle.")
            
            self.phi =0
            self.lEditPhi.setText(str(self.phi))
        if self.plotVisDict and self.btnPlay.isChecked():
            key = list(self.plotVisDict.keys())[0]
            self.phi_idx = self.analyser.ml.find_nearest(self.analyser.dfDict[key]['phi'], self.phi)[0]
            self.refreshPlot()
    
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

    try:

        app = QApplication(sys.argv)
        win = PolDataViewerWindow('../config/polDataViewerConfig.yml')
        win.show()
        app.exec()
    except Exception as e:
        raise e