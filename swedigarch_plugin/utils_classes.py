"""
/***************************************************************************
 Swedigarch Geotools is a tool for field archaeologist to transform their
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
"""Collection of small help classes"""

import traceback
from enum import Enum
from . import utils as Utils
from . import export_utils as ExportUtils

class Site:
    """Class to hold and handle site information"""
    def __init__(self, conn, data_frame):
        self.name_value = {}
        self.site_id = '' # Default value, empty string if missing in Intrasis db
        meta_site_id = Utils.get_meta_id(conn, Utils.Intrasis.ATTRIBUTE_SITE_ID_META_ID)
        for row in data_frame.itertuples(index=False):
            if row.MetaId == meta_site_id:
                self.site_id = row.Value
            elif row.LongText:
                try:
                    self.description = ExportUtils.rtf_to_text(row.Text)
                except UnicodeEncodeError as ex:
                    traceback.print_exc()
                    print(f"Error in rtf_to_text() for site {ex}")
                    self.description = "<invalid rtf>"
                self.name_value[row.Label] = self.description
            else:
                self.name_value[row.Label] = row.Value

    def get_fields(self):
        """Return a list of available fields"""
        return list(self.name_value.keys())

    def get_field_value(self, value_name):
        """Return string for given value_name or empty string if not set (not exist)"""
        if value_name in self.name_value:
            return self.name_value[value_name]
        return ""

class IconType(Enum):
    """ObjectColor IconType"""
    CIRCLE = 0
    SQUARE = 1

class SymbolException (Exception):
    """Raised on error with symbology in SymbolBuilder class"""

    def __init__(self, message = None):
        self.message = message
        super().__init__(message)
