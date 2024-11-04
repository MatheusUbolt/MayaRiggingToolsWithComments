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

class LimbRiggerWidget(QWidget):# Main class for the Limb Rigging Tool UI.
    def __init__(self):
        mainWindow: QMainWindow = LimbRiggerWidget.GetMayaMainWindow()# Get Maya's main window instance.

        for existing in mainWindow.findChildren(QWidget, LimbRiggerWidget.GetWindowUniqueId()):# Check for existing instances.
            existing.deleteLater()# Delete any existing instances of this widget.

        super().__init__(parent=mainWindow) # Initialize the QWidget with Maya's main window as the parent.
        
        self.setWindowTitle("Limb Rigging Tool")# Set the window title.
        self.setWindowFlags(Qt.Window)# Set window type to Qt Window.
        self.setObjectName(LimbRiggerWidget.GetWindowUniqueId())# Set a unique object name for the window.
        self.controllerSize = 15# Set the default controller size.

        self.masterLayout = QVBoxLayout()# Create the main vertical layout.
        self.setLayout(self.masterLayout)# Set the main layout to the widget.

        hintLabel = QLabel("Please Select the Root, Middle and End Joint of your Limb:")# Add instructional label.
        self.masterLayout.addWidget(hintLabel)# Add label to the layout.

        controllerSizeCtrlLayout = QHBoxLayout()# Create horizontal layout for controller size adjustment.
        self.masterLayout.addLayout(controllerSizeCtrlLayout)# Add the horizontal layout to the main layout.

        controllerSizeCtrlLayout.addWidget(QLabel("Controller Size: "))# Label for controller size adjustment.
        controllerSizeSlider = QSlider()# Slider to adjust controller size.
        controllerSizeSlider.setValue(self.controllerSize)# Set initial slider value.
        controllerSizeSlider.setMinimum(1)# Set minimum slider value.
        controllerSizeSlider.setMaximum(30)# Set maximum slider value.
        controllerSizeSlider.setOrientation(Qt.Horizontal)# Set slider orientation to horizontal.
        controllerSizeCtrlLayout.addWidget(controllerSizeSlider)# Add slider to the layout.
        self.sizeDisplayLabel = QLabel(str(self.controllerSize))# Display the current controller size.
        controllerSizeSlider.valueChanged.connect(self.ControllerSizeChanged)# Connect slider to size change method.
        controllerSizeCtrlLayout.addWidget(self.sizeDisplayLabel) # Add size display label to the layout.


        rigLimButton = QPushButton("Rig The Limb")# Button to rig the limb.
        rigLimButton.clicked.connect(self.RigTheLimb)# Connect button to the rigging function.
        self.masterLayout.addWidget(rigLimButton)# Add button to the main layout.

    def RigTheLimb(self):# Main function to rig the limb.
        selection = mc.ls(sl=True)# Get the selected joints.

        rootJnt = selection[0]# Root joint.
        midJnt = selection[1]# Middle joint.
        endJnt = selection[2]# End joint.

        rootFKCtrl, rootFKCtrlGrp = self.CreateFKForJnt(rootJnt)# Create FK control for root joint.
        midFKCtrl, midFKCtrlGrp = self.CreateFKForJnt(midJnt)# Create FK control for mid joint.
        endFKCtrl, endFKCtrlGrp = self.CreateFKForJnt(endJnt)# Create FK control for end joint.

        mc.parent(midFKCtrlGrp, rootFKCtrl)# Parent mid FK control to root FK control.
        mc.parent(endFKCtrlGrp, midFKCtrl)# Parent end FK control to mid FK control.

        ikEndCtrlName, ikEndCtrlGrpName, midIkCtrlName, midIkCtrlGrpName, ikHandleName = self.CreateIkControl(rootJnt, midJnt, endJnt) # Create IK controls.

        ikfkBlendCtrlName = "ac_ikfk_blend_" + rootJnt# Name for the IK/FK blend control.
        mel.eval(f"curve -d 1 -n {ikfkBlendCtrlName} -p -1 1 0 -p -1 3 0 -p 1 3 0 -p 1 1 0 -p 3 1 0 -p 3 -1 0 -p 1 -1 0 -p 1 -3 0 -p -1 -3 0 -p -1 -1 0 -p -3 -1 0 -p -3 1 0 -p -1 1 0 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 ;")# Create the IK/FK blend control shape.
        ikfkBlendCtrlGrpName = ikfkBlendCtrlName + "_grp"# Name for IK/FK blend control group.
        mc.group(ikfkBlendCtrlName, n = ikfkBlendCtrlGrpName)# Group the IK/FK blend control.

        rootJntPosVals = mc.xform(rootJnt, t=True, q=True, ws=True)# Get the world-space position of the root joint.
        rootJntPos = MVector(rootJntPosVals[0], rootJntPosVals[1], rootJntPosVals[2])# Convert to MVector.
        ikfkBlendCtrlPos = rootJntPos + MVector(rootJntPos.x, 0, 0)# Offset IK/FK blend control position.
        mc.move(ikfkBlendCtrlPos[0], ikfkBlendCtrlPos[1], ikfkBlendCtrlPos[2], ikfkBlendCtrlGrpName)# Move IK/FK blend control to position.

        ikfkBlendAttrName = "ikfk_blend"# Attribute name for IK/FK blending.
        mc.addAttr(ikfkBlendCtrlName, ln=ikfkBlendAttrName, k=True, min = 0, max = 1)# Add IK/FK blend attribute.

        mc.expression(s=f"{rootFKCtrlGrp}.v=1-{ikfkBlendCtrlName}.{ikfkBlendAttrName};") # Set visibility of FK based on blend.
        mc.expression(s=f"{ikEndCtrlGrpName}.v={ikfkBlendCtrlName}.{ikfkBlendAttrName}")# Set visibility of IK controls.
        mc.expression(s=f"{midIkCtrlGrpName}.v={ikfkBlendCtrlName}.{ikfkBlendAttrName}")# Set visibility for mid IK.
        mc.expression(s=f"{ikHandleName}.ikBlend={ikfkBlendCtrlName}.{ikfkBlendAttrName}")# Set IK blend value.

        endJntOrientConstraint = mc.listConnections(endJnt, s=True, t= 'orientConstraint')[0]# Get orient constraint for end joint.
        mc.expression(s=f"{endJntOrientConstraint}.{endFKCtrl}W0=1-{ikfkBlendCtrlName}.{ikfkBlendAttrName};")# FK influence expression.
        mc.expression(s=f"{endJntOrientConstraint}.{ikEndCtrlName}W1={ikfkBlendCtrlName}.{ikfkBlendAttrName};")# IK influence expression.

        topGrpName = f"{rootJnt}_rig_grp"# Name for top rig group.

        mc.group([rootFKCtrlGrp, ikEndCtrlGrpName, midIkCtrlGrpName,ikfkBlendCtrlGrpName], n = topGrpName)# Group all components.

    def CreateFKForJnt(self, jnt):# Method to create an FK control for a joint
        fkCtrlName = "ac_fk_" + jnt# Name for FK control.
        fkCtrlGrpName = fkCtrlName + "_grp"# Name for FK control group.
        mc.circle(n=fkCtrlName, r=self.controllerSize, nr=(1,0,0)) # Create FK control circle.
        mc.group(fkCtrlName, n = fkCtrlGrpName)# Group FK control
        mc.matchTransform(fkCtrlGrpName, jnt)# Match FK control position with joint.
        mc.orientConstraint(fkCtrlName, jnt)# Constrain joint orientation to FK control.
        return fkCtrlName, fkCtrlGrpName

    def CreateIkControl(self, rootJnt, midJnt, endJnt): # Creates the IK control
        #wrist controller
        ikEndCtrlName = "ac_ik_" + endJnt# Name fir IK control
        mel.eval(f"curve -d 1 -n {ikEndCtrlName} -p -0.5 0.5 0.5 -p 0.5 0.5 0.5 -p 0.5 0.5 -0.5 -p -0.5 0.5 -0.5 -p -0.5 0.5 0.5 -p -0.5 -0.5 0.5 -p -0.5 -0.5 -0.5 -p -0.5 0.5 -0.5 -p -0.5 -0.5 -0.5 -p 0.5 -0.5 -0.5 -p 0.5 -0.5 0.5 -p -0.5 -0.5 0.5 -p -0.5 -0.5 -0.5 -p 0.5 -0.5 -0.5 -p 0.5 -0.5 0.5 -p 0.5 0.5 0.5 -p 0.5 0.5 -0.5 -p 0.5 -0.5 -0.5 -p 0.5 -0.5 0.5 -p -0.5 -0.5 0.5 -p -0.5 0.5 0.5 -p 0.5 0.5 0.5 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 -k 13 -k 14 -k 15 -k 16 -k 17 -k 18 -k 19 -k 20 -k 21 ;")# Creates shape for IK control.
        mc.scale(self.controllerSize, self.controllerSize, self.controllerSize, ikEndCtrlName, r=True)# Scales the IK control to match the user-defined controller size.
        mc.makeIdentity(ikEndCtrlName, apply = True) #freeze transformation
        ikEndCtrlGrpName = ikEndCtrlName + "_grp"# Creates name for IK group.
        mc.group(ikEndCtrlName, n = ikEndCtrlGrpName)# Groups the control into its own group
        mc.matchTransform(ikEndCtrlGrpName, endJnt)# Matches the group's position and orientation to the end joint's transform.
        mc.orientConstraint(ikEndCtrlName, endJnt) # Constrains the end joint's orientation to follow the IK control.

        #ik handle
        ikHandleName = "ikHandle_" + endJnt# Names the IK handle
        mc.ikHandle(n=ikHandleName, sj=rootJnt, ee=endJnt, sol="ikRPsolver") # Creates an IK handle from the root joint to the end joint using an IKRP solver (rotation-plane IK).

        rootJntPosVals = mc.xform(rootJnt, q=True, t=True, ws=True) #getting the world space(ws=True) translate(t+True) of the root Jnt, as a list of 3 values
        rootJntPos = MVector(rootJntPosVals[0], rootJntPosVals[1], rootJntPosVals[2])# Converts the root joint's position into a MVector

        endJntPosVals = mc.xform(endJnt, q=True, t=True, ws=True) # Queries the world space position of the end joint.
        endJntPos = MVector(endJntPosVals[0], endJntPosVals[1], endJntPosVals[2])# Converts the end joint's position into a MVector.

        poleVectorVals = mc.getAttr(ikHandleName + ".poleVector")[0]# Retrieves the pole vector attribute values from the IK handle.
        poleVector = MVector(poleVectorVals[0], poleVectorVals[1], poleVectorVals[2])# Converts the pole vector to an MVector and normalizes it
        poleVector.normalize()

        vectorToEnd = endJntPos - rootJntPos# Calculates the direction vector from the root joint to the end joint.
        LimbDirOffset: MVector = vectorToEnd/2

        poleVectorDirOffset = poleVector * LimbDirOffset.length()# Scales the pole vector direction by the limb's half-length to position it correctly.
        midIkCtrlPos = rootJntPos + LimbDirOffset + poleVectorDirOffset

        midIkCtrlName = "ac_ik_" + midJnt# Names the pole vector control.
        mc.spaceLocator(n=midIkCtrlName)

        midIkCtrlGrpName = midIkCtrlName + "_grp"# Creates group name.
        mc.group(midIkCtrlName, n = midIkCtrlGrpName)# Groups it
        mc.move(midIkCtrlPos.x,midIkCtrlPos.y, midIkCtrlPos.z, midIkCtrlGrpName)# Moves the group to the calculated pole vector control position.


        mc.parent(ikHandleName, ikEndCtrlName) # Parents the IK handle to the IK control
        mc.poleVectorConstraint(midIkCtrlName, ikHandleName)# Applies a pole vector constraint to control the IK handle's rotation with the pole vector control.
        mc.setAttr(ikHandleName+".v",0)# Sets the IK handle's visibility to 0 to keep it hidden in the scene.

        return ikEndCtrlName, ikEndCtrlGrpName,midIkCtrlName, midIkCtrlGrpName, ikHandleName






    def ControllerSizeChanged(self, sliderVal):
        self.sizeDisplayLabel.setText(str(sliderVal))
        self.controllerSize = sliderVal



    @staticmethod
    def GetMayaMainWindow():
        mainWindow = omui.MQtUtil.mainWindow()
        return wrapInstance(int(mainWindow), QMainWindow)
    
    @staticmethod
    def GetWindowUniqueId():
        return "53ef72c18116817fe7265383a6591a6f"

def Run():
    LimbRiggerWidget().show()

