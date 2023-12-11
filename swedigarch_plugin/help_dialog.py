# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Swedigarch plugin is a tool for field archaeologist to transform their
 data from proprietary to open format.

 Copyright (C) 2023 Swedigarch
 
 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or 
 any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <https://www.gnu.org/licenses/>.

 Contact: swedigarch@uu.se
 Address: Swedigarch, Department of Archaeology and Ancient History, 
		  Uppsala University, Box 626, 751 26 Uppsala, Sweden

***************************************************************************/
"""

import os
import ast
from PyQt5.QtCore import Qt, QUrl, QSettings
from qgis.PyQt import uic, QtWidgets
from . import utils as Utils

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'help_dialog.ui'))

class HelpDialog(QtWidgets.QDialog, FORM_CLASS):
    """Help dialog"""
    def __init__(self, page_url:str, title:str, parent=None) -> None:
        """Constructor."""
        super(HelpDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint |
                            Qt.CustomizeWindowHint |
                            Qt.WindowTitleHint)
        self.button_box.button(QtWidgets.QDialogButtonBox.Close).setText(self.tr("Close"))
        self.button_box.accepted.connect(self.on_close)
        if title is not None:
            title = self.tr(title)
            self.setWindowTitle(title)

        url = None
        if page_url.startswith('http'):
            url = QUrl(page_url)
        else:
            # Uses localy stored html page
            location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
            user_locale = QSettings().value("locale/userLocale")[0 : 2]
            content_name = f'{user_locale}_{page_url}'
            local_filename = os.path.join(location, 'help', content_name)
            url = QUrl.fromLocalFile(local_filename)
        self.webView.load(url)

    def on_close(self) -> None:
        """Dialog closed"""
        self.close()

    @staticmethod
    def show_help(section:str) -> None:
        """Show help for give section, if it exist, else do nothing"""
        file_data = Utils.load_resource("help/help_sections.json")
        dictionary = ast.literal_eval(file_data)
        if section in dictionary:
            url_info = dictionary[section]
        else:
            return

        url = url_info["url"]
        title = url_info["title"]
        help_dlg = HelpDialog(url, title)
        help_dlg.exec_()
