# syntax.py

from PyQt4.QtCore import QRegExp
from PyQt4.QtGui import QColor, QTextCharFormat, QFont, QSyntaxHighlighter


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        QSyntaxHighlighter.__init__(self, document)

        # Syntax styles specific for Gaffer
        self.styles = {
            'keyword':  self.text_format("#CC7832", 'bold'),
            'operator': self.text_format("#FFC68D"),
            'brace':    self.text_format("#EEEEEE"),
            'defclass': self.text_format("#EEEEEE", 'bold'),
            'string': self.text_format("#8AA779"),
            'string2':  self.text_format("#8AA779", 'italic'),
            'comment':  self.text_format("#808080", 'italic'),
            'self':     self.text_format("#8A653B", 'italic'),
            'numbers':  self.text_format("#6897BB")
        }

        # Python keywords
        self.keywords = [
            'and', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'exec', 'finally',
            'for', 'from', 'global', 'if', 'import', 'in',
            'is', 'lambda', 'not', 'or', 'pass', 'print',
            'raise', 'return', 'try', 'while', 'yield',
            'None', 'True', 'False',
        ]

        # Python operators
        self.operators = [
            '=',
            # Comparison
            '==', '!=', '<', '<=', '>', '>=',
            # Arithmetic
            '\+', '-', '\*', '/', '//', '\%', '\*\*',
            # In-place
            '\+=', '-=', '\*=', '/=', '\%=',
            # Bitwise
            '\^', '\|', '\&', '\~', '>>', '<<',
        ]

        # Python braces
        self.braces = [
            '\{', '\}', '\(', '\)', '\[', '\]',
        ]

        self.block_state_id = {
            "'":   2,
            '"':   3,
            "'''": 4,
            '"""': 5,
            '#':   6
        }

        rules = []

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, 'keyword') for w in self.keywords]
        rules += [(r'%s' % o, 0, 'operator') for o in self.operators]
        rules += [(r'%s' % b, 0, 'brace') for b in self.braces]

        # All other rules
        rules += [
            # 'self'
            (r'\bself\b', 0, 'self'),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)', 1, 'defclass'),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)', 1, 'defclass'),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, 'numbers'),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, 'numbers'),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, 'numbers'),
        ]

        # Build a QRegExp for each pattern
        self.rules = [(QRegExp(pat), index, fmt) for (pat, index, fmt) in rules]

        self.formats = {}

    @staticmethod
    def text_format(color, style=''):
        _color = QColor(color)

        _format = QTextCharFormat()
        _format.setForeground(_color)

        if 'bold' in style:
            _format.setFontWeight(QFont.Bold)

        if 'italic' in style:
            _format.setFontItalic(True)

        return _format

    def isSubStrEscaped(self, substr_index):
        if substr_index <= 0:
            return False
        text = self.currentBlock().text()
        index = substr_index-1
        escape_count = 0
        while index >= 0 and text[index] == "\\":
            escape_count += 1
            index -= 1
        return escape_count % 2 != 0

    def parseStringsAndComments(self, text):
        strings_and_comments = {"string": [], "string2": [], "comment": []}

        # find triple quote continuation from last block
        if self.previousBlockState() in [self.block_state_id["'''"], self.block_state_id['"""']]:
            strings_and_comments["string2"] = [(0, len(text))]
            # Keep in the same state as before since we are currently inside a triple-quote string
            self.setCurrentBlockState(self.previousBlockState())
        else:
            # On every block we start from scratch unless there is a triple-quote string from previous blocks
            self.setCurrentBlockState(-1)

        index = 0
        while index < len(text):
            add_to_index = 1
            char = str(text[index])
            if char in ["'", '"']:
                # Triple-quote strings
                if index+3 <= len(text) and str(text[index:index+3]) in ["'''", '"""'] and not self.isSubStrEscaped(index):
                    potential_triple_quote = str(text[index:index+3])
                    # Start a new triple-quote string block
                    if self.currentBlockState() < 2:
                        add_to_index = 3
                        strings_and_comments["string2"].append((index, len(text)))
                        self.setCurrentBlockState(self.block_state_id[potential_triple_quote])
                    # Close old triple-quote string block
                    elif self.currentBlockState() == self.block_state_id[potential_triple_quote]:
                        add_to_index = 3
                        last_index = len(strings_and_comments["string2"])-1
                        start = strings_and_comments["string2"][last_index][0]
                        strings_and_comments["string2"][last_index] = (start, index-start+3)
                        self.setCurrentBlockState(-1)
                # Single-quote strings
                elif not self.isSubStrEscaped(index):
                    # Start a new string block
                    if self.currentBlockState() < 2:
                        block_state = self.block_state_id[char]
                        strings_and_comments["string"].append((index, len(text)))
                        self.setCurrentBlockState(block_state)
                    # Close old string block only if it matches the starting quote type
                    elif self.currentBlockState() == self.block_state_id[char]:
                        block_state = -1
                        last_index = len(strings_and_comments["string"])-1
                        start = strings_and_comments["string"][last_index][0]
                        strings_and_comments["string"][last_index] = (start, index-start+1)
                        self.setCurrentBlockState(block_state)
            # Comments
            elif char == "#" and self.currentBlockState() < 2:
                strings_and_comments["comment"].append((index, len(text)-index))
                self.setCurrentBlockState(self.block_state_id["#"])

            index += add_to_index

        return strings_and_comments

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text.
        """
        # Start by parsing strings and comments since they are mutually exclusive escape-tokens of each other

        self.formats = self.parseStringsAndComments(text)

        # Set Format and collect all indices that have text.
        indecies_with_text = []
        for format_style, indecies in self.formats.items():
            format_style = self.styles[format_style]
            for start, str_len in indecies:
                self.setFormat(start, str_len, format_style)
                indecies_with_text.extend(range(start, start+str_len))

        # Do other syntax formatting
        for expression, nth, style in self.rules:
            index = expression.indexIn(text, 0)
            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)
                length = len(expression.cap(nth))

                # skip matches that are already strings
                if index not in indecies_with_text:
                    self.setFormat(index, length, self.styles[style])
                    if style not in self.formats.keys():
                        self.formats[style] = [(index, index+length)]
                    else:
                        self.formats[style].append((index, index+length))
                index = expression.indexIn(text, index + length)

