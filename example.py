import numpy as np
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui

class MyApp(QtGui.QMainWindow):

    def __init__(self, parent=None):
        super(MyApp, self).__init__(parent=parent)

        self.mainbox = QtGui.QWidget()
        self.setCentralWidget(self.mainbox)
        self.setAcceptDrops(True)                   # accept MIME style file drops
        lay = QtGui.QVBoxLayout(self.mainbox)
        self.canvas = pg.GraphicsLayoutWidget()
        lay.addWidget(self.canvas)

        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(1)
        self.timer.start()

        self.plot  = self.canvas.addPlot(title="Updating plot")
        self.curve = self.plot.plot(pen='y')
        self.data  = np.random.normal(size=(10,1000))
        self.ptr   = 0

        self.timer.timeout.connect(self.update)

        # Pause button in a toolbar. Pauses when checked
        self.toolbar = self.addToolBar("Pause")
        self.playScansAction = QtGui.QAction("Pause", self)
        self.playScansAction.triggered.connect(self.playScansPressed)
        self.playScansAction.setCheckable(True)
        self.toolbar.addAction(self.playScansAction)
        
        self.droppedFiles = []
        self.files = []

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.droppedFiles = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in self.droppedFiles:
            if f not in self.files and f.endswith(".pkl"):
                print(f)
                self.files.append(f)

    def playScansPressed(self):
        if self.playScansAction.isChecked():
            self.timer.stop()
        else:
            self.timer.start()

    def update(self):
        self.curve.setData(self.data[self.ptr % 10])
        if self.ptr == 0:
            self.plot.enableAutoRange('xy', False)  # stop auto-scaling after the first data set is plotted
        self.ptr += 1


if __name__ == "__main__":
    
    app = QtGui.QApplication(sys.argv)
    this_app = MyApp()
    this_app.show()
    sys.exit(app.exec_())

