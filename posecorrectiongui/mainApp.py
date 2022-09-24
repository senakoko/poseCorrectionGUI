import sys
from pathlib import Path
import yaml
import cv2
import pandas as pd

from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QIcon, QKeySequence, QScreen, QPainter
from PySide6.QtWidgets import (QApplication, QFileDialog,
                               QMainWindow, QToolBar)

from setRunParameters import set_run_parameters
from processFrame import process_frame
from qImageProcess import qt_image_process
from saveLastFrameNumber import save_last_frame_number
from plotTrackedPoints import plot_tracked_points
from swapLabels import swap_labels, swap_label_sequences
from propagateFrame import propagate_frame
from relabelPoints import relabel_points
from updateH5file import update_h5file


class MainGUI(QMainWindow):

    def __init__(self, video_name=None, h5_name=None):
        super().__init__()
        self.parameters = set_run_parameters()
        self.filters = "Any File (*)"
        self.scale_factor = self.parameters.scale_factor
        # Initialize values
        self.video_name = video_name
        self.h5_name = h5_name
        self.click_label_button = Qt.RightButton
        self.event_use_wasd_keys(use_wasd=False)

        # Using Configuration Files ############################################################################
        config_path = Path('.') / 'config.yaml'

        with open(config_path, 'r') as fr:
            config = yaml.load(fr, Loader=yaml.FullLoader)

        self.last_frame_path = Path('.') / 'last_video_frame.yaml'

        if self.last_frame_path.exists():
            with open(self.last_frame_path, 'r') as fr:
                self.last_frame_data = yaml.load(fr, Loader=yaml.FullLoader)

        self.videos_main_path = str(config['videos_main_path'][0])
        self.h5files_main_path = str(config['h5files_path'][0])

        self.body_parts = config['body_parts']
        self.skeleton = config['skeleton']
        self.animals_list = config['animals']
        self.animals_identity = self.animals_list.copy()
        self.animals_identity.append('both')

        self.body_parts_keys = {}
        for i, v in enumerate(self.body_parts):
            self.body_parts_keys[v] = i

        self.animal_bodypoints = {}
        self.bodypoints1 = {}
        self.bodypoints2 = {}
        self.index = 0
        self.frame_number = 0

        self.create_ui()
        self.imageLabel = QtWidgets.QLabel()

        self.setCentralWidget(self.imageLabel)

    def create_ui(self) -> None:
        self.create_action()
        self.create_frame_action()
        self.create_widgets()
        self.event_go_to_frame()
        self.event_frame_slider()
        self.event_swap_frame()
        self.event_swap_sequence()
        self.event_propagate_forward()
        self.event_propagate_backward()
        self.event_relabel_animals()
        self.create_menu_bar()
        self.create_toolbar()

    def create_menu_bar(self) -> None:
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction(self.open_video_action)
        self.file_menu.addAction(self.open_h5_action)

        # self.edit_menu = self.menuBar().addMenu("&Edit Video")
        # self.edit_menu.addAction(self.next_frame_action)
        # self.edit_menu.addAction(self.previous_frame_action)
        # self.edit_menu.addAction(self.jump_forward_action)
        # self.edit_menu.addAction(self.jump_backward_action)
        # self.edit_menu.addAction(self.mark_start_action)
        # self.edit_menu.addAction(self.mark_end_action)

        self.help_menu = self.menuBar().addMenu("&Help")
        self.help_menu.addAction(self.help_action)

    def create_toolbar(self) -> None:
        self.top_toolbar = QToolBar('Load Video and H5file Toolbar')
        self.addToolBar(self.top_toolbar)
        self.top_toolbar.addAction(self.open_video_action)
        self.top_toolbar.addAction(self.open_h5_action)
        self.top_toolbar.addSeparator()
        self.top_toolbar.addWidget(self.frame_number_widget)

        self.left_side_toolbar = QToolBar('Frame Toolbar')
        self.addToolBar(Qt.LeftToolBarArea, self.left_side_toolbar)
        # self.left_side_toolbar.addWidget(self.frame_number_widget)
        self.left_side_toolbar.addSeparator()
        self.left_side_toolbar.addWidget(QtWidgets.QLabel('Go To Frame: '))
        self.left_side_toolbar.addWidget(self.goto_frame)
        self.left_side_toolbar.addAction(self.next_frame_action)
        self.left_side_toolbar.addAction(self.previous_frame_action)
        self.left_side_toolbar.addSeparator()
        self.left_side_toolbar.addAction(self.jump_forward_action)
        self.left_side_toolbar.addWidget(self.jump_number)
        self.left_side_toolbar.addAction(self.jump_backward_action)
        self.left_side_toolbar.addWidget(self.swap_labels)

        self.right_side_toolbar = QToolBar('Sequence Toolbar')
        self.addToolBar(Qt.RightToolBarArea, self.right_side_toolbar)
        self.right_side_toolbar.addWidget(QtWidgets.QLabel('Swap Sequence of Frames'))
        self.right_side_toolbar.addAction(self.mark_start_action)
        self.right_side_toolbar.addWidget(self.frame_from)
        self.right_side_toolbar.addAction(self.mark_end_action)
        self.right_side_toolbar.addWidget(self.frame_to)
        self.right_side_toolbar.addWidget(self.swap_sequence_button)
        self.right_side_toolbar.addSeparator()
        self.right_side_toolbar.addWidget(QtWidgets.QLabel('Select Animal'))
        self.right_side_toolbar.addWidget(self.prop_animal)
        self.right_side_toolbar.addWidget(self.prop_forward)
        self.right_side_toolbar.addWidget(self.prop_line)
        self.right_side_toolbar.addWidget(self.prop_backward)
        self.right_side_toolbar.addSeparator()
        self.right_side_toolbar.addWidget(self.relabel_button)
        self.right_side_toolbar.addWidget(self.label_animal)
        self.right_side_toolbar.addWidget(self.scrollArea)
        self.right_side_toolbar.addWidget(self.done_label_button)
        self.right_side_toolbar.addSeparator()
        self.right_side_toolbar.addWidget(self.label_with_left_click)

        self.slider_toolbar = QToolBar('Slider Dock')
        self.addToolBar(Qt.BottomToolBarArea, self.slider_toolbar)
        self.slider_toolbar.addWidget(self.frame_slider_widget)

    def create_action(self) -> None:
        icon = QIcon.fromTheme("document-open")
        self.open_video_action = QAction(icon, '&Load Video File',
                                         self, shortcut=QKeySequence.Open,
                                         statusTip="Open an video file",
                                         triggered=self.open_vid_file)

        self.open_h5_action = QAction(QIcon(), '&Load H5 File',
                                      self, shortcut=QKeySequence("Ctrl+i"),
                                      statusTip="Open H5 file",
                                      triggered=self.open_h5_file)

        self.help_action = QAction(QIcon(), '&Show Shortcuts',
                                   self, shortcut=QKeySequence("Ctrl+p"),
                                   triggered=self.show_shortcuts)

    def create_frame_action(self) -> None:
        self.next_frame_action = QAction(QIcon(), '&Next Frame', self,
                                         toolTip="Go to the next Frame",
                                         triggered=self.event_next_frame,
                                         shortcut=QKeySequence(self.next_frame_key)
                                         )

        self.previous_frame_action = QAction(QIcon(), 'Previous Frame',
                                             toolTip="Go to the previous Frame",
                                             triggered=self.event_previous_frame,
                                             shortcut=QKeySequence(self.previous_frame_key)
                                             )

        self.jump_forward_action = QAction(QIcon(), 'Jump Forward',
                                           toolTip="Jump Forward N Frames",
                                           triggered=self.event_jump_forward,
                                           shortcut=QKeySequence(self.jump_forward_key)
                                           )

        self.jump_backward_action = QAction(QIcon(), 'Jump Backward',
                                            toolTip="Jump Backward N Frames",
                                            triggered=self.event_jump_backward,
                                            shortcut=QKeySequence(self.jump_backward_key)
                                            )

        self.mark_start_action = QAction(QIcon(), 'Mark Start',
                                         toolTip="Mark Start to Swap Sequence",
                                         triggered=self.event_mark_start,
                                         shortcut=QKeySequence("Ctrl+,")
                                         )

        self.mark_end_action = QAction(QIcon(), 'Mark End',
                                       toolTip="Mark End to Swap Sequence",
                                       triggered=self.event_mark_end,
                                       shortcut=QKeySequence("Ctrl+.")
                                       )

    def create_widgets(self) -> None:
        self.frame_number_widget = QtWidgets.QLabel()
        font = self.frame_number_widget.font()
        font.setPointSize(15)
        self.frame_number_widget.setFont(font)

        self.goto_frame = QtWidgets.QLineEdit()
        self.goto_frame.setPlaceholderText('Enter Frame #')
        self.goto_frame.setFixedWidth(100)
        self.goto_frame.textChanged.connect(self.event_go_to_frame)

        self.jump_number = QtWidgets.QLineEdit()
        self.jump_number.setPlaceholderText('Enter steps')
        self.jump_number.setFixedWidth(100)
        self.jump_number.returnPressed.connect(self.event_disable_lineedit)

        self.swap_labels = QtWidgets.QPushButton('Swap Labels')
        font = self.swap_labels.font()
        font.setPointSize(15)
        self.swap_labels.setFont(font)
        self.swap_labels.clicked.connect(self.event_swap_frame)
        self.swap_labels.setShortcut(QKeySequence("Ctrl+'"))

        self.frame_from = QtWidgets.QLineEdit()
        self.frame_from.setPlaceholderText('From')
        self.frame_from.setFixedWidth(120)

        self.frame_to = QtWidgets.QLineEdit()
        self.frame_to.setPlaceholderText('To')
        self.frame_to.setFixedWidth(120)

        self.swap_sequence_button = QtWidgets.QPushButton('Swap Sequence')
        font = self.swap_sequence_button.font()
        font.setPointSize(15)
        self.swap_sequence_button.setFont(font)
        self.swap_sequence_button.clicked.connect(self.event_swap_sequence)
        self.swap_sequence_button.setShortcut(QKeySequence("Ctrl+/"))

        self.prop_animal = QtWidgets.QComboBox()
        # Add animals to propagate list
        self.prop_animal.addItems(self.animals_identity)
        self.prop_animal.setFixedWidth(100)
        self.prop_animal.setCurrentText(self.animals_identity[-1])

        self.prop_forward = QtWidgets.QPushButton('Propagate Forward')
        self.prop_forward.setFont(font)
        self.prop_forward.setFixedWidth(150)
        self.prop_forward.clicked.connect(self.event_propagate_forward)
        self.prop_forward.setShortcut(QKeySequence("Ctrl+]"))

        self.prop_line = QtWidgets.QLineEdit()
        self.prop_line.setFont(font)
        self.prop_line.setFixedWidth(100)
        self.prop_line.setPlaceholderText('Enter steps')
        self.prop_line.returnPressed.connect(self.event_disable_lineedit)

        self.prop_backward = QtWidgets.QPushButton('Propagate Backward')
        self.prop_backward.setFont(font)
        self.prop_backward.setFixedWidth(150)
        self.prop_backward.clicked.connect(self.event_propagate_backward)
        self.prop_backward.setShortcut(QKeySequence("Ctrl+["))

        self.relabel_button = QtWidgets.QPushButton('Relabel')
        self.relabel_button.setFont(font)
        self.relabel_button.setFixedWidth(150)
        self.relabel_button.clicked.connect(self.event_relabel_animals)
        self.relabel_button.setShortcut(QKeySequence("Ctrl+l"))

        self.label_animal = QtWidgets.QComboBox()
        # Add animals to label list
        self.label_animal.addItems(self.animals_list)
        self.label_animal.setFont(font)
        self.label_animal.setFixedWidth(100)
        self.label_animal.currentTextChanged.connect(self.event_update_selection)

        self.body_parts_list = QtWidgets.QListWidget()
        # Add body parts to widgets
        self.body_parts_list.addItems(self.body_parts)
        self.body_parts_list.setCurrentRow(0)
        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setWidget(self.body_parts_list)
        self.scrollArea.setFixedWidth(120)
        self.scrollArea.setFixedHeight(200)

        self.done_label_button = QtWidgets.QPushButton('Done Labeling')
        self.done_label_button.setFont(font)
        self.done_label_button.setFixedWidth(150)
        self.done_label_button.clicked.connect(self.event_done_labeling)
        self.done_label_button.setShortcut(QKeySequence("Ctrl+;"))

        self.label_with_left_click = QtWidgets.QCheckBox('Left Click Label')
        self.label_with_left_click.setFont(font)
        self.label_with_left_click.setFixedWidth(150)
        # self.label_with_left_click.stateChanged.connect(self.event_label_with_left_click)

        self.frame_slider_widget = QtWidgets.QSlider(Qt.Horizontal)
        self.frame_slider_widget.setRange(0, 100)
        self.frame_slider_widget.setSingleStep(1)
        self.frame_slider_widget.valueChanged[int].connect(self.event_frame_slider)

    # Load the video file
    def open_vid_file(self) -> None:
        try:
            self.video_name, self.filter_name = QFileDialog.getOpenFileName(self,
                                                                            caption="Open file",
                                                                            filter=self.filters,
                                                                            dir=self.videos_main_path)
            self.cap = cv2.VideoCapture(self.video_name)
            self.length = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
            self.frame_slider_widget.setRange(0, self.length)
            ret, self.image = self.cap.read()
            self.image = process_frame(self.image, scale_factor=self.parameters.scale_factor)
            self.imageLabel.setPixmap(qt_image_process(self.image))
            self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
            if self.last_frame_path.exists():
                if self.video_name in self.last_frame_data.keys():
                    self.move_to_last_labeled_frame()

            # Fix the size of the GUI
            # self.setFixedWidth(self.width())
            # self.setFixedHeight(self.height())
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Unable to load the Video \n'
                                                         'Make sure to load right the video')
        except FileNotFoundError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'File  does not exist \n'
                                                         'You might need to restart the GUI')

    def move_to_last_labeled_frame(self) -> None:
        last_frame_output = QtWidgets.QMessageBox.question(self, 'Last Frame',
                                                           'Do you want to go to the last labeled frame',
                                                           buttons=(QtWidgets.QMessageBox.StandardButton.Yes |
                                                                    QtWidgets.QMessageBox.StandardButton.No),
                                                           defaultButton=QtWidgets.QMessageBox.StandardButton.Yes)
        if last_frame_output == QtWidgets.QMessageBox.StandardButton.Yes:
            self.frame_number = self.last_frame_data[self.video_name]
            self.cap.set(1, self.frame_number)
            ret, self.image = self.cap.read()
            self.image = process_frame(self.image, scale_factor=self.parameters.scale_factor)
            self.frame_slider_widget.setValue(self.frame_number)
            self.imageLabel.setPixmap(qt_image_process(self.image))
            self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")

    # Load the H5 file and plot it
    def open_h5_file(self) -> None:
        try:
            self.h5_name, self.filter_name = QFileDialog.getOpenFileName(self,
                                                                         caption="Open file",
                                                                         filter="*.h5",
                                                                         dir=self.h5files_main_path)
            self.h5 = pd.read_hdf(self.h5_name)
            self.image = process_frame(self.image, scale_factor=int(1 / self.scale_factor))
            self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
            self.image = process_frame(self.image, scale_factor=self.scale_factor)
            self.imageLabel.setPixmap(qt_image_process(self.image))
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    def show_shortcuts(self) -> None:
        QtWidgets.QMessageBox.about(self, "Show Shortcuts",
                                    "Next Frame\t\t --> Right Arrow \n"
                                    "Previous Frame\t --> Left Arrow \n"
                                    "Jump Forward\t --> Up Arrow \n"
                                    "Jump Backward\t --> Down Arrow \n"
                                    "Swap Labels\t --> Ctrl + ' \n"
                                    "Mark Start\t\t --> Ctrl + , \n"
                                    "Mark End\t\t --> Ctrl + . \n"
                                    "Swap Sequence\t --> Ctrl + / \n"
                                    "Propagate Forward\t --> Ctrl + ] \n"
                                    "Propagate Backward\t --> Ctrl + [ \n"
                                    "Relabel\t\t --> Ctrl + l \n"
                                    "Done Labeling\t --> Ctrl + ; \n"
                                    )

    # Sliding through the video
    def event_frame_slider(self) -> None:
        try:
            self.frame_number = int(self.frame_slider_widget.value())
            self.goto_frame.setText(str(self.frame_number))
            if self.video_name:
                self.cap.set(1, self.frame_number)
                ret, self.image = self.cap.read()

                if self.h5_name:
                    self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
                else:
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Unable to read the Video \n'
                                                         'Reload it again')

    # Moving forward through the video one frame at a time.
    def event_next_frame(self) -> None:
        try:
            self.frame_number += 1
            if self.frame_number > self.length:
                self.frame_number = self.length
            self.goto_frame.setText(str(self.frame_number))
            self.frame_slider_widget.setValue(self.frame_number)
            if self.video_name:
                self.cap.set(1, self.frame_number)
                ret, self.image = self.cap.read()
                if self.h5_name:
                    self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
                else:
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    # Moving backward through the video one frame at a time.
    def event_previous_frame(self) -> None:
        try:
            self.frame_number -= 1
            if self.frame_number < 0:
                self.frame_number = 0
            self.goto_frame.setText(str(self.frame_number))
            self.frame_slider_widget.setValue(self.frame_number)
            if self.video_name:
                self.cap.set(1, self.frame_number)
                ret, self.image = self.cap.read()
                if self.h5_name:
                    self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
                else:
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    # Jump forward a set number of frames
    def event_jump_forward(self) -> None:
        try:
            self.val_num = self.jump_number.text()
            if self.val_num == '':
                self.val_num = '15'
            self.jump_number.setText(str(self.val_num))
            try:
                self.frame_number += int(self.val_num)
            except ValueError:
                QtWidgets.QMessageBox.warning(self, 'ValueError', 'invalid number entered - integer required')
            if self.frame_number > self.length:
                self.frame_number = self.length
            self.goto_frame.setText(str(self.frame_number))
            self.frame_slider_widget.setValue(self.frame_number)
            if self.video_name:
                self.cap.set(1, self.frame_number)
                ret, self.image = self.cap.read()
                if self.h5_name:
                    self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
                else:
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    # Jump backward a set number of frames
    def event_jump_backward(self) -> None:
        try:
            self.val_num = self.jump_number.text()
            if self.val_num == '':
                self.val_num = '15'
            self.jump_number.setText(str(self.val_num))
            try:
                self.frame_number -= int(self.val_num)
            except ValueError:
                QtWidgets.QMessageBox.warning(self, 'ValueError', 'invalid number entered - integer required')
            if self.frame_number < 0:
                self.frame_number = 0
            self.goto_frame.setText(str(self.frame_number))
            self.frame_slider_widget.setValue(self.frame_number)
            if self.video_name:
                self.cap.set(1, self.frame_number)
                ret, self.image = self.cap.read()
                if self.h5_name:
                    self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
                else:
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    # Going to a specific frame in the video
    def event_go_to_frame(self) -> None:
        try:
            self.goto_num = self.goto_frame.text()
            if self.goto_num == '':
                self.goto_num = '0'
            try:
                self.frame_number = int(self.goto_num)
            except ValueError:
                QtWidgets.QMessageBox.warning(self, 'ValueError', 'invalid number entered')
            self.goto_frame.setText(str(self.frame_number))
            self.frame_slider_widget.setValue(self.frame_number)
            if self.video_name:
                if self.frame_number > self.length:
                    self.frame_number = self.length
                self.cap.set(1, self.frame_number)
                ret, self.image = self.cap.read()
                if self.h5_name:
                    self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
                else:
                    self.image = process_frame(self.image, scale_factor=self.scale_factor)
                    self.imageLabel.setPixmap(qt_image_process(self.image))
                    self.frame_number_widget.setText(f"Frames: {self.frame_number} / {self.length}")
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Frame does not exits')

    # Get the frame number to start the sequence swap
    def event_mark_start(self) -> None:
        self.frame_from.setText(str(self.frame_number))

    # Get the frame number to end the sequence swap
    def event_mark_end(self) -> None:
        self.frame_to.setText(str(self.frame_number))

    # Swap the labels for mis-tracked points on the animals for a single frame
    def event_swap_frame(self) -> None:
        try:
            if self.h5_name:
                swap_labels(self.h5, self.frame_number, self.h5_name)
                self.h5 = pd.read_hdf(self.h5_name)
                self.image = process_frame(self.image, scale_factor=int(1 / self.scale_factor))
                self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                self.image = process_frame(self.image, scale_factor=self.scale_factor)
                self.imageLabel.setPixmap(qt_image_process(self.image))
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    # Swap the labels for mis-tracked points on the animals for a sequence of frames.
    # Only works for two tracked animals.
    def event_swap_sequence(self) -> None:
        try:
            if self.h5_name:
                try:
                    self.from_frame_number = int(self.frame_from.text())
                    self.to_frame_number = int(self.frame_to.text())
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, 'ValueError', 'invalid number entered - integer required')
                if self.to_frame_number == self.length:
                    self.to_frame_number = self.to_frame_number
                else:
                    self.to_frame_number += 1
                swap_label_sequences(self.h5, self.from_frame_number, self.to_frame_number, self.h5_name)
                self.h5 = pd.read_hdf(self.h5_name)
                self.image = process_frame(self.image, scale_factor=int(1 / self.scale_factor))
                self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                self.image = process_frame(self.image, scale_factor=self.scale_factor)
                self.imageLabel.setPixmap(qt_image_process(self.image))
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    # Propagate rightly tracked body points from the previous image to the current one
    def event_propagate_forward(self) -> None:
        try:
            if self.h5_name:
                steps = self.prop_line.text()
                if steps == '':
                    steps = '1'
                    self.prop_line.setText(steps)
                try:
                    steps = int(steps)
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, 'ValueError', 'invalid number entered - integer required')
                if steps == 1:
                    steps += 1
                animal_ident = self.prop_animal.currentText()
                propagate_frame(self.h5, self.frame_number, self.h5_name, 'forward', steps, animal_ident)
                self.h5 = pd.read_hdf(self.h5_name)
                self.image = process_frame(self.image, scale_factor=int(1 / self.scale_factor))
                self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                self.image = process_frame(self.image, scale_factor=self.scale_factor)
                self.imageLabel.setPixmap(qt_image_process(self.image))
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    # Propagate rightly tracked body points from the previous image to the current one
    def event_propagate_backward(self) -> None:
        try:
            if self.h5_name:
                steps = self.prop_line.text()
                if steps == '':
                    steps = '1'
                    self.prop_line.setText(steps)
                try:
                    steps = int(steps)
                except ValueError:
                    QtWidgets.QMessageBox.warning(self, 'ValueError', 'invalid number entered - integer required')
                animal_ident = self.prop_animal.currentText()
                propagate_frame(self.h5, self.frame_number, self.h5_name, 'backward', steps, animal_ident)
                self.h5 = pd.read_hdf(self.h5_name)
                self.image = process_frame(self.image, scale_factor=int(1 / self.scale_factor))
                self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
                self.image = process_frame(self.image, scale_factor=self.scale_factor)
                self.imageLabel.setPixmap(qt_image_process(self.image))
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    def event_relabel_animals(self) -> None:
        if self.video_name:
            self.cap.set(1, self.frame_number)
            ret, self.image = self.cap.read()
            self.image = process_frame(self.image, scale_factor=self.parameters.scale_factor)
            self.imageLabel.setPixmap(qt_image_process(self.image))
            self.animal_bodypoints = {}
            self.bodypoints1 = {}
            self.bodypoints2 = {}
            self.index = 0

    def event_done_labeling(self) -> None:
        try:
            self.cap.set(1, self.frame_number)
            ret, self.image = self.cap.read()
            new_points = relabel_points(self.animal_bodypoints, self.body_parts, self.scale_factor)
            update_h5file(new_points, self.h5, self.frame_number, self.h5_name)
            self.h5 = pd.read_hdf(self.h5_name)
            self.image = plot_tracked_points(self.image, self.h5, self.frame_number, self.skeleton)
            self.image = process_frame(self.image, scale_factor=self.scale_factor)
            self.imageLabel.setPixmap(qt_image_process(self.image))
        except AttributeError:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Load the Video first')

    def event_update_selection(self) -> None:
        self.index = 0
        self.body_parts_list.setCurrentRow(self.index)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.label_with_left_click.isChecked():
            self.click_label_button = Qt.LeftButton
        else:
            self.click_label_button = Qt.RightButton

        if event.button() == self.click_label_button:
            canvas = self.imageLabel.pixmap()
            painter = QPainter(canvas)
            pen = painter.pen()
            pen.setWidth(6)
            animal_id = self.label_animal.currentText()
            if self.label_animal.currentIndex() == 1:
                pen.setColor(QtGui.QColor('blue'))
            else:
                pen.setColor(QtGui.QColor('red'))
            painter.setPen(pen)
            self.calculate_image_pos()
            globalPos = event.scenePosition().toPoint()
            mouse_x_value, mouse_y_value = globalPos.x(), globalPos.y()
            x_value = mouse_x_value - self.image_x_value
            y_value = mouse_y_value - self.image_y_value
            start_point = (x_value, y_value)
            draw_value = QPoint(x_value, y_value)
            painter.drawPoint(draw_value)
            painter.end()

            bpt = self.body_parts[self.body_parts_list.currentRow()]
            if animal_id == self.animals_list[1]:
                self.bodypoints2[bpt] = start_point
                self.animal_bodypoints[animal_id] = self.bodypoints2
            else:
                self.bodypoints1[bpt] = start_point
                self.animal_bodypoints[animal_id] = self.bodypoints1

            self.index = self.body_parts_keys[bpt]
            self.index += 1
            if self.index == len(self.body_parts):
                self.index = 0
            self.body_parts_list.setCurrentRow(self.index)
            self.imageLabel.setPixmap(canvas)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.top_toolbar.setFocus()

    def event_use_wasd_keys(self, use_wasd: bool = True) -> None:
        if use_wasd:
            self.next_frame_key = 'd'
            self.previous_frame_key = 'a'
            self.jump_forward_key = 'w'
            self.jump_backward_key = 's'
        else:
            self.next_frame_key = 'right'
            self.previous_frame_key = 'left'
            self.jump_forward_key = 'up'
            self.jump_backward_key = 'down'

    def event_disable_lineedit(self) -> None:
        self.top_toolbar.setFocus()

    def calculate_image_pos(self) -> None:
        # check if any toolbar is at the starting corner
        self.image_x_value = self.imageLabel.pos().x()
        self.image_y_value = self.imageLabel.pos().y()

    def my_exit_handler(self) -> None:
        try:
            if self.video_name:
                save_last_frame_number(self.frame_number, self.video_name)
        except AttributeError:
            return


def main():
    app = QApplication([])
    widget = MainGUI()
    app.aboutToQuit.connect(widget.my_exit_handler)
    widget.resize(800, 800)
    widget.setWindowTitle('Pose Correction GUI')
    # SrcSize = QScreen.availableGeometry(QApplication.primaryScreen())
    # frmX = (SrcSize.width() - widget.width()) / 2
    # frmY = (SrcSize.height() - widget.height()) / 2
    # widget.move(frmX, frmY)
    widget.move(40, 40)
    widget.show()
    widget.top_toolbar.setFocus()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
