# Import Maya commands as 'mc' and MEL commands as 'mel'
import maya.cmds as mc
import maya.mel as mel

# Import Maya vector for 3D manipulation and OpenMayaUI for UI interaction
from maya.OpenMaya import MVector
import maya.OpenMayaUI as omui

# Import PySide2 for GUI creation and shiboken2 to handle QWidget instances in Maya
from PySide2.QtWidgets import QVBoxLayout, QWidget, QPushButton, QMainWindow, QHBoxLayout, QGridLayout, QLineEdit, QLabel, QSlider
from PySide2.QtCore import Qt
from shiboken2 import wrapInstance


#copy/paste the following on the MEL Maya script Editor to connect VSC to Maya then Alt + Shift + M to run the code
#commandPort -n "localhost:7001" -stp "mel";

class TrimSheetBuilderWidget(QWidget): # Define custom QWidget for the trim sheet builder
    def __init__(self):
        mainWindow: QMainWindow = TrimSheetBuilderWidget.GetMayaMainWindow()# Get Maya's main window as the parent

        # Delete any existing instances of the widget to avoid duplicates
        for existing in mainWindow.findChildren(QWidget, TrimSheetBuilderWidget.GetWindowUniqueId()):
            existing.deleteLater()

        super().__init__(parent=mainWindow)# Initialize the QWidget with Maya's main window as its parent
        
        self.setWindowTitle("Trim sheet Builder")# Set the window title
        self.setWindowFlags(Qt.Window)# Set window flags for independent window behavior
        self.setObjectName(TrimSheetBuilderWidget.GetWindowUniqueId())# Unique object name for the widget
        
        self.shell = []# Initialize list to store selected UV shells

        # Create main layout and add sub-sections for the widget
        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)
        self.CreateInitializationSection()# Call function to create initialization UI
        self.CreateManipulationSection()# Call function to create manipulation UI

    def FillShellToU1V1(self):# Method to scale UV shell to fit within U1V1 space
        width, height = self.GetShellSize()# Get current shell dimensions
        su = 1 / width  # Calculate scale factor for U direction
        sv = 1 / height  # Calculate scale factor for V direction
        self.ScaleShell(su, sv)  # Scale shell to fit within UV space
        self.MoveToOrigin()  # Move shell to origin after scaling

    def GetShellSize(self):  # Method to get UV shell dimensions
        min, max = self.GetShellBound()  # Get min and max bounds of the UV shell
        height = max[1] - min[1]  # Calculate height of the shell
        width = max[0] - min[0]  # Calculate width of the shell
        return width, height  # Return width and height as a tuple

    def ScaleShell(self, u, v):  # Method to scale UV shell based on specified U and V factors
        mc.polyEditUV(self.shell, su=u, sv=v, r=True)  # Apply scaling to UV shell

    def MoveShell(self, u, v):  # Method to move the UV shell by a specified U and V offset
        width, height = self.GetShellSize()  # Get current shell dimensions
        uAmt = u * width  # Calculate movement amount in U direction
        vAmt = v * height  # Calculate movement amount in V direction
        mc.polyEditUV(self.shell, u=uAmt, v=vAmt)  # Move UV shell by specified amounts

    def CreateManipulationSection(self):# Create UI section for UV shell manipulation controls
        sectionLayout = QVBoxLayout()# Define vertical layout for manipulation section
        self.masterLayout.addLayout(sectionLayout)# Add section to main layout

        # Create and add "Turn" button to rotate UV shell
        turnBtn = QPushButton("Turn")
        turnBtn.clicked.connect(self.TurnShell)
        sectionLayout.addWidget(turnBtn)

        # Create and add "Move to Origin" button to reset UV shell position
        moveToOriginBtn = QPushButton("Move to Origin")
        moveToOriginBtn.clicked.connect(self.BackToOrigin)
        sectionLayout.addWidget(moveToOriginBtn)

        # Create and add "Fill UV" button to scale shell to fit U1V1
        fillU1V1Btn = QPushButton("Fill UV")
        fillU1V1Btn.clicked.connect(self.FillShellToU1V1)
        sectionLayout.addWidget(fillU1V1Btn)

        # Add scaling buttons to scale shell in U and V directions
        halfUBtn = QPushButton("Half U")
        halfUBtn.clicked.connect(lambda : self.ScaleShell(0.5, 1))
        sectionLayout.addWidget(halfUBtn)

        halfVBtn = QPushButton("Half V")
        halfVBtn.clicked.connect(lambda : self.ScaleShell(1, 0.5))
        sectionLayout.addWidget(halfVBtn)

        doubleUBtn = QPushButton("Double U")
        doubleUBtn.clicked.connect(lambda : self.ScaleShell(2, 1))
        sectionLayout.addWidget(doubleUBtn)

        doubleVBtn = QPushButton("Double V")
        doubleVBtn.clicked.connect(lambda : self.ScaleShell(1, 2))
        sectionLayout.addWidget(doubleVBtn)

        # Create grid layout for directional movement buttons
        moveSection = QGridLayout()
        sectionLayout.addLayout(moveSection)

        # Add directional buttons for moving the shell in the UV space
        moveUpBtn = QPushButton("^")
        moveUpBtn.clicked.connect(lambda : self.MoveShell(0, 1))
        moveSection.addWidget(moveUpBtn, 0 , 1)

        moveDownBtn = QPushButton("v")
        moveDownBtn.clicked.connect(lambda : self.MoveShell(0, -1))
        moveSection.addWidget(moveDownBtn, 2 , 1)

        moveLeftBtn = QPushButton("<")
        moveLeftBtn.clicked.connect(lambda : self.MoveShell(-1, 0))
        moveSection.addWidget(moveLeftBtn, 1 , 0)

        moveRightBtn = QPushButton(">")
        moveRightBtn.clicked.connect(lambda : self.MoveShell(1, 0))
        moveSection.addWidget(moveRightBtn, 1 , 2)

    def GetShellBound(self):# Method to get min and max UV coordinates of the shell
        uvs = mc.polyListComponentConversion(self.shell, toUV=True)# Convert shell to UV components
        uvs = mc.ls(uvs, fl=True)# Flatten UV list
        firstUV = mc.polyEditUV(uvs[0], q=True)# Get coordinates of the first UV
        minU = firstUV[0]# Initialize min and max U
        maxU = firstUV[0]
        minV = firstUV[1]# Initialize min and max V
        maxV = firstUV[1]
        for uv in uvs:# Loop through all UVs in the shell
            uvCoord = mc.polyEditUV(uv, q=True)# Query UV coordinates
            if uvCoord[0] < minU:# Update min U if necessary
                minU = uvCoord[0]
            
            if uvCoord[0] >maxU:# Update max U if necessary
                minU = uvCoord[0]

            if uvCoord [1] < minV:# Update min V if necessary
                minU = uvCoord[1]

            if uvCoord[1] > maxV:# Update max V if necessary
                minU = uvCoord[1]
        return [minU, minV], [maxU, maxV]# Return bounds as min and max UV points
    
    def BackToOrigin(self):# Method to move UV shell to origin in UV space
        minCoord, maxCoord = self.GetShellBound()# Get UV bounds of the shell
        mc.polyEditUV(self.shell, u=-minCoord[0], v=-minCoord[1])# Move shell to origin

    def TurnShell(self):# Method to rotate UV shell by 90 degrees
        mc.select(self.shell, r=True)# Select the UV shell
        mel.eval("polyRotateUVs 90 0")# Rotate shell by 90 degrees using MEL

    def CreateInitializationSection(self):# Create UI section for initial shell setup
        sectionLayout = QHBoxLayout()# Define horizontal layout for initialization section
        self.masterLayout.addLayout(sectionLayout)# Add layout to the main layout

        # Create and add "Select Shell" button to select the shell
        selectShellBtn = QPushButton("Select Shell")
        selectShellBtn.clicked.connect(self.SelectShell)
        sectionLayout.addWidget(selectShellBtn)

        # Create and add "Unfold" button to unfold UV shell
        unfoldBtn = QPushButton("Unfold")
        unfoldBtn.clicked.connect(self.UnfoldShell)
        sectionLayout.addWidget(unfoldBtn)

        # Create and add "Cut and Unfold" button to cut and unfold shell
        cutAndUnfoldBtn = QPushButton("Cut and Unfold")
        cutAndUnfoldBtn.clicked.connect(self.CutAndUnfoldShell)
        sectionLayout.addWidget(cutAndUnfoldBtn)

    def CutAndUnfoldShell(self):# Method to cut selected edges and unfold the UV shell
        edges = mc.ls(sl=True)# Get selected edges
        mc.polyProjection(self.shell, type="Planar", md="c")# Apply a planar projection to the UV shell
        mc.polyMapCut(edges)# Cut the UVs at the selected edges
        mc.u3dUnfold(self.Shell)# Unfold the shell after cutting
        mel.eval("textOrientShells")# Orient the UV shells using MEL to improve layout

    def UnfoldShell(self):# Method to apply a planar projection and unfold the UV shell
        mc.polyProjection(self.shell, type="Planar", md="c")# Project shell as a planar map
        mc.u3dUnfold(self.shell)# Unfold the shell using Maya's unfold tool


    def SelectShell(self):# Method to select UV shell components
        self.shell = mc.ls(sl=True, fl=True)# Store selected components as the shell


    @staticmethod
    def GetMayaMainWindow():# Static method to get the main Maya window as a parent
        mainWindow = omui.MQtUtil.mainWindow()# Get the Maya main window's pointer
        return wrapInstance(int(mainWindow), QMainWindow)# Convert pointer to QMainWindow instance
    
    @staticmethod
    def GetWindowUniqueId():# Static method to get a unique identifier for the widget
        return "53ef72c88116817fe7265383a6591a6f"# Return unique ID for identifying the widget instance

def Run():# Function to create and display the TrimSheetBuilderWidget
    TrimSheetBuilderWidget().show()# Show the widget when the script is run
    
