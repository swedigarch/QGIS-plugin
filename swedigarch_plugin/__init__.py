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

from .swedigarch_export import SwedigarchPlugin

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SwedigarchPlugin class from file swedigarch_export.py.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    return SwedigarchPlugin(iface)
