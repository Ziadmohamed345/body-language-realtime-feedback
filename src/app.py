import sys
import typing
from PyQt6.QtCore import QObject
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
import cv2
from time import time
from comp import Pose_Detection as ps , Motion_Detection as md
from comp import Emotion_Detection as ed
from utils import fps


stylesheet = """
    QWidget {
        background-color: #894fda;
    }
    QLabel {
        color: #FFFFFF;
        font-weight: bold;
        font-size: 16px;
    }
    QLabel#TitleLabel {
        background-color: #b198f6;
        font-size: 48px;
    }
    QPushButton {
        background-color: #1aacb6;
        border: none;
        color: #FFFFFF;
        font-weight: bold;
        font-size: 16px;
        padding: 10px;
    }
    QPushButton:hover {
        background-color: #b198f6;
    }
"""

current_pose = "pose"
current_fps = 0
current_motion = 0

class MenuWindow(QWidget):
    def __init__(self) -> None:
        super(MenuWindow, self).__init__()

        self.setMinimumSize(700, 400)
        self.setMaximumSize(800, 600)

        self.VBL = QVBoxLayout()

        self.setWindowTitle("Presentation Assistant V0.1")

        # Title Label
        self.TitleLBL = QLabel("Presentation Assistant V0.1")
        self.TitleLBL.setObjectName("TitleLabel")
        self.TitleLBL.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.VBL.addWidget(self.TitleLBL)

        # About Label
        self.AboutLBL = QLabel("This is a program that helps you analyze your presentation performance.\nChoose a mode to start.")
        self.AboutLBL.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.VBL.addWidget(self.AboutLBL)

        self.VBL.addSpacing(20)

        # Full Body Detection Button
        self.FullBodyBTN = QPushButton("Offline Presentation")
        self.FullBodyBTN.clicked.connect(self.start_fullbody_window)
        self.VBL.addWidget(self.FullBodyBTN)

        # Facial Detection Button
        self.FacialBTN = QPushButton("Online Presentation")
        self.FacialBTN.clicked.connect(self.start_facial_window)
        self.VBL.addWidget(self.FacialBTN)

        self.setLayout(self.VBL)

        self.setStyleSheet(stylesheet)

    def start_fullbody_window(self):
        self.hide()
        self.fullbody_window = FullBodyWindow(body = True)
        self.fullbody_window.show()
    
    def start_facial_window(self):
        self.hide()
        self.facial_window = FullBodyWindow(body= False)
        self.facial_window.show()

class FullBodyWindow(QWidget):
    def __init__(self, body) -> None:
        super(FullBodyWindow , self).__init__()

        self.body = body

        self.HBL = QHBoxLayout()
        self.VBL = QVBoxLayout()

        self.VBL.addLayout(self.HBL)

        # The box that holds the image
        self.FeedLabel = QLabel()
        self.HBL.addWidget(self.FeedLabel)

        # Data to show
        # "FPS: " + str(current_fps) + "\n"
        #                       "Motion: " + str(current_motion) + "\n"
        #                       "Pose: " + str(current_pose)
        self.DataLBL = QLabel("")
        self.DataLBL.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.HBL.addWidget(self.DataLBL)

        # the Menu button
        self.MenuBTN = QPushButton("Menu")
        self.MenuBTN.clicked.connect(self.menu_window)
        self.VBL.addWidget(self.MenuBTN)


        # the thread that holds creates the camera feed
        self.Worker1 = Worker1(body,self)
        self.Worker1.start()
        self.Worker1.ImageUpdate.connect(self.ImageUpdateSlot)
        self.Worker1.label_dict.connect(self.DictUpdateSlot)
        self.setLayout(self.VBL)

        self.setStyleSheet(stylesheet)

    def ImageUpdateSlot(self,Image):
        self.FeedLabel.setPixmap(QPixmap.fromImage(Image))

    def DictUpdateSlot(self,dict1):
        if(self.body):
            self.DataLBL.setText("FPS: " + str(dict1['Fps']) + "\n"
                              "Motion: " + str(dict1["Motion"]) + "\n"
                              "Pose: " + str(dict1['Pose']))
        else:
            self.DataLBL.setText("FPS: " + str(dict1['Fps']) + "\n"
                              "Emotion: " + str(dict1["Emotion"]))
            
        
    def menu_window(self):
        self.Worker1.stop()
        self.hide()
        self.menu_window = MenuWindow()
        self.menu_window.show()

class Worker1(QThread):

    def __init__(self,body, parent: QObject):
        super().__init__(parent)
        self.body = body

    ImageUpdate = pyqtSignal(QImage)
    label_dict = pyqtSignal(dict)

    
    def run(self):
        
        # used for the camra feed while loop
        self.ThreadActive = True
        output_dict = {'Fps':0,"Pose":"",
                  "Motion":0, "Emotion":""}
        
        # set camera resolution
        Capture = cv2.VideoCapture(0)
        Capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        Capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1024)
        
        # for Fps tracking
        Time_start = 0
        Fps = 30

        while self.ThreadActive:
            
            ret , frame = Capture.read()
            frame = cv2.flip(frame, 1)

            TIME_PASSED = time() - Time_start

            # if the amount of time passed is more than 1/fps 
            # and camera feed is succeful
            if not (TIME_PASSED > 1. / Fps and ret):
                continue
            Time_start = time()
            
            
            # Puts the current FPS of the camera feed
            output_dict['Fps'] = fps.get_fps(frame)

            if(self.body):
                # Puts the current pose's label and landmarks
                output_dict['Pose'] = ps.detect_pose(frame)
                # Puts the amount of motion detected
                output_dict['Motion'] = md.detect_motion(frame)
            
            else:
                output_dict['Emotion'] = ed.detect_emotion(frame)
            



            # converts the image from BGR to RGB for display
            frame =  cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # to QImage
            ConvertToQtFormat = QImage(frame.data, frame.shape[1],frame.shape[0],
                                        QImage.Format.Format_RGB888)
            # sends the image to the main window
            Pic = ConvertToQtFormat.scaled(640,512, Qt.AspectRatioMode.KeepAspectRatio)

            self.label_dict.emit(output_dict)
            self.ImageUpdate.emit(Pic)


    def stop(self):
        """
        Fuction that exits the thread and stops the camera feed while loop
        """
        self.ThreadActive = False
        self.quit()
        self.wait()
        
if __name__ == "__main__":
    App = QApplication(sys.argv)
    Root = MenuWindow()
    Root.show()
    sys.exit(App.exec())