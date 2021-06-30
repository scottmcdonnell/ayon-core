import sys
sys.path.append(r"C:\Users\iLLiCiT\PycharmProjects\pype3\.venv\Lib\site-packages")
from Qt import QtWidgets, QtCore

from control import PublisherController
from widgets import SubsetAttributesWidget


class PublisherWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PublisherWindow, self).__init__(parent)

        self._first_show = True
        # TODO Title, Icon, Stylesheet

        main_frame = QtWidgets.QWidget(self)

        # Header
        context_label = QtWidgets.QLabel(main_frame)

        # Content
        content_widget = QtWidgets.QWidget(main_frame)

        # Subset widget
        subset_widget = QtWidgets.QWidget(content_widget)

        subset_view = QtWidgets.QTreeView(subset_widget)
        subset_attributes = SubsetAttributesWidget(subset_widget)

        subset_layout = QtWidgets.QHBoxLayout(subset_widget)
        subset_layout.addWidget(subset_view, 0)
        subset_layout.addWidget(subset_attributes, 1)

        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(subset_widget)

        # Footer
        footer_widget = QtWidgets.QWidget(self)

        create_btn = QtWidgets.QPushButton("Create", footer_widget)
        message_input = QtWidgets.QLineEdit(footer_widget)
        validate_btn = QtWidgets.QPushButton("Validate", footer_widget)
        publish_btn = QtWidgets.QPushButton("Publish", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addWidget(create_btn, 0)
        footer_layout.addWidget(message_input, 1)
        footer_layout.addWidget(validate_btn, 0)
        footer_layout.addWidget(publish_btn, 0)

        # Main frame
        main_frame_layout = QtWidgets.QVBoxLayout(main_frame)
        main_frame_layout.addWidget(context_label, 0)
        main_frame_layout.addWidget(content_widget, 1)
        main_frame_layout.addWidget(footer_widget, 0)

        # Add main frame to this window
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(main_frame)

        create_btn.clicked.connect(self._on_create_clicked)
        validate_btn.clicked.connect(self._on_validate_clicked)
        publish_btn.clicked.connect(self._on_publish_clicked)

        self.main_frame = main_frame

        self.context_label = context_label

        self.footer_widget = footer_widget
        self.message_input = message_input
        self.validate_btn = validate_btn
        self.publish_btn = publish_btn

        controller = PublisherController()

        self.controller = controller

        # DEBUGING
        self.set_context_label(
            "<project>/<hierarchy>/<asset>/<task>/<workfile>"
        )
        # self.setStyleSheet("border: 1px solid black;")

    def showEvent(self, event):
        super(PublisherWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self.reset()

    def reset(self):
        self.controller.reset()

    def set_context_label(self, label):
        self.context_label.setText(label)

    def _on_create_clicked(self):
        print("Creation!!!")

    def _on_validate_clicked(self):
        print("Validation!!!")

    def _on_publish_clicked(self):
        print("Publishing!!!")


def main():
    """Main function for testing purposes."""

    app = QtWidgets.QApplication([])
    window = PublisherWindow()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
