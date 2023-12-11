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
"""constant"""

from enum import Enum

class Intrasis:
    """Intrasis constants"""
    #region Intrasis definitions
    CLASS_SITE_META_ID = 1
    """MetaId of the Class Site in Intrasis"""

    ATTRIBUTE_SITE_ID_META_ID = 96
    """MetaId for attribut SiteId"""

    CLASS_STAFF_META_ID = 3
    """MetaId of the Class Staff/Personal in Intrasis"""

    CLASS_GEOOBJECT_META_ID = 23
    """MetaId of the Class GeoObject in Intrasis"""
    #endregion

class RetCode(Enum):
    """Return codes, from call to export_to_geopackage in geopackage_export.py"""

    #region Export script return codes

    EXPORT_OK = 0
    """OK, export done"""

    UNKNOWN_ERROR = 1
    """Unknown error"""

    ARGUMENT_ERROR = 2
    """Argument error"""

    TERMINATED_BY_QGIS = 10
    """Canceled from QGIS"""

    #region Databas relaterade
    GENERIC_DB_CONNECTION_ERROR = 100
    """General database connection error"""

    INVALID_LOGIN = 101
    """Invalid login (username/password)"""

    COULD_NOT_CONNECT_TO_SERVER = 102
    """Unable to connect, no response from server."""

    DATABASE_IS_NOT_INTRASIS_DB = 110
    """The database is not an Intrasis database"""

    DATABASE_ACCESS_ERROR = 120
    """Access problems when reading database objects"""
    #endregion

    #region Export katalog relaterade
    UNKNOWN_ERROR_WITH_EXPORT_FOLDER = 200
    """Unknown error with the export directory"""

    EXPORT_FOLDER_DOES_NOT_EXIST = 201
    """The export directory does not exist"""

    ACCESS_ERROR_TO_EXPORT_FOLDER = 202
    """Permission error while accessing the directory"""
    #endregion

    #endregion

class WriterError(Enum):
    """WriteError return code, QgsRasterFileWriter.writeRaster return codes"""

    NoError = 0
    SourceProviderError = 1
    DestProviderError = 2
    CreateDatasourceError = 3
    WriteError = 4
    NoDataConflict = 5
