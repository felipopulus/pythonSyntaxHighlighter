# editor.py

from PySide2 import QtGui, QtWidgets
import syntax

app = QtWidgets.QApplication([])
editor = QtWidgets.QPlainTextEdit()
highlight = syntax.PythonHighlighter(editor.document())
editor.show()

# Load syntax.py into the editor for demo purposes
infile = open('syntax.py', 'r')
editor.setPlainText(infile.read())

app.exec_()