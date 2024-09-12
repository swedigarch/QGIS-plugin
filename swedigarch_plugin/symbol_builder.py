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
"""SymbolBuilder"""

import traceback
import struct
from typing import Union
from enum import Enum
import psycopg2
import pandas as pd
from time import sleep
from xml.dom import minidom
from qgis.core import QgsWkbTypes
from . import utils as Utils
from .utils_classes import SymbolException

class GeometryType(Enum):
    """Definitions of Intrasis geometry types"""
    NotSet = -1
    Multipoint = 0
    Point = 1
    Polygon = 2
    Polyline = 3
    Square = 4
    Raster = 5

class PointSymbolStyle(Enum):
    """Definitions of SimpleMarker symbol styles"""
    NotSet = -1
    Circle = 0
    Square = 1
    Cross = 2
    X = 3
    Diamond = 4
    Triangle = 5

class LineSymbolStyle(Enum):
    """Definitions of LineSymbol styles"""
    NotSet = -1
    Solid = 0
    Dashed = 1
    Dotted = 2
    DashDot = 3
    DashDotDot = 4

class SimpleFillStyle(Enum):
    """Definitions of ESRI simple fill style"""
    Solid = 0
    Hollow = 1
    Horizontal = 2
    Vertical = 3
    ForwardDiagonal = 4
    BackwardDiagonal = 5
    Cross = 6
    DiagonalCross = 7

class SymbolDef:
    """Class to hold symbol definition"""
    def __init__(self, row):
        self.sym_id = row.SymbolId
        self.class_id = row.ClassId
        self.font = row.Font
        self.size = row.SymbolSize
        self.index = row.SymbolIndex
        self.color = SymbolColor.parse(row.Color)
        self.sym_type = row.Type
        if self.sym_type == "SimpleFillSymbol":
            self.qml_sym_type = "fill"
        elif self.sym_type == "SimpleLineSymbol":
            self.qml_sym_type = "line"
        elif self.sym_type == "SimpleMarkerSymbol" or self.sym_type == "CharacterMarkerSymbol":
            self.qml_sym_type = "marker"
        self.border_width = row.BorderWidth
        self.border_color = SymbolColor.parse(row.BorderColor)
        self.class_name = row.Class
        self.name = row.Name
        self.geo_object_type = GeometryType[row.GeoObjectType]
        self.label = f"{self.class_name} ({self.name})"

    def get_class_type(self) -> str:
        """Get layer symbol class"""
        if self.sym_type == "SimpleMarkerSymbol":
            return "SimpleMarker"
        elif self.sym_type == "CharacterMarkerSymbol":
            return "FontMarker"
        elif self.sym_type == "SimpleLineSymbol":
            return "SimpleLine"
        elif self.sym_type == "SimpleFillSymbol":
            return "SimpleFill"
        return "SimpleMarker"

    def get_marker_symbol_type(self) -> Union[PointSymbolStyle, None]:
        """Get PointSymbolStyle from symbol index"""
        if self.get_class_type() != "SimpleMarker":
            return None
        symbol_type = PointSymbolStyle(self.index)
        return symbol_type

    def get_line_symbol_style(self) -> Union[LineSymbolStyle, None]:
        """Get SimpleLineSymbol from symbol index"""
        if self.sym_type != "SimpleLineSymbol":
            return None
        symbol_type = LineSymbolStyle(self.index)
        return symbol_type

    def get_simple_fill_style(self) -> Union[SimpleFillStyle, None]:
        """Get SimpleFillStyle from symbol index"""
        if self.sym_type != "SimpleFillSymbol":
            return None
        simple_fill_style = SimpleFillStyle(self.index)
        return simple_fill_style

    def __str__(self):
        return f"SymbolDef({self.sym_id}, ClassId: {self.class_id}, type: {self.sym_type}, name: {self.name}, label: {self.label})"

    @staticmethod
    def size_to_text(size:int) -> str:
        """Convert size number to text"""
        if size is None:
            return "0"
        return str(size).replace(',', '.')

class SymbolColor:
    """Class to hande symbol color conversions"""
    def __init__(self, db_color:int):
        try:
            my_bytes = struct.pack("i", db_color)
            self.red = my_bytes[0]
            self.green = my_bytes[1]
            self.blue = my_bytes[2]
            self.alpha = 255
        except Exception as err:
            print(f"Error in SymbolColor({db_color}) {err}")

    def to_string(self) -> str:
        """Convert to string representation"""
        return f"{self.red},{self.green},{self.blue},{self.alpha}"

    @staticmethod
    def to_text(symbol_color: 'SymbolColor') -> str:
        """Function to convert symbol color to text, can handle if it is None"""
        if symbol_color is not None:
            return symbol_color.to_string()
        return "0,0,0,0"

    @staticmethod
    def parse(db_value:int):
        """Parse db value function"""
        try:
            if db_value is not None and db_value != -1 and Utils.is_nan(db_value) is False:
                return SymbolColor(int(db_value))
            return None
        except Exception as err:
            print(f"Error in SymbolColor.parse() {err}")
            return None

class SymbolBuilder:
    """Help class to build symbol definitons"""
    def __init__(self, conn:psycopg2.extensions.connection, detailed_print_outs:bool=True):
        self.conn = conn
        self.all_symbols = {}
        self.detailed_print_outs = detailed_print_outs
        self.load_class_geometries()
        self.load_class_symbols()
        self.load_used_symbol_ids()
        #print(f"keys: {self.class_symbols.keys()}")
        #print(f"class_symbols: {len(self.class_symbols)}")

    def build_symbols_for_layer(self, filter_string:str) -> str:
        """Function that build the QGIS qml symbol definition file"""
        try:
            symbol_defs = self.load_symbols_defs_for_layer(filter_string)
            if len(symbol_defs) == 0:
                return None

            geometry_type = SymbolBuilder.filter_string_to_gometry_type(filter_string)
            if geometry_type != GeometryType.NotSet:
                class_ids = self.geometry_classes[geometry_type]
                symbols = self.get_symbols_for_classes(class_ids, geometry_type)
                #print(f"class_ids: {class_ids}, symbols.count: {len(symbols)}")

                symbol_defs = []
                for symbol_id in symbols:
                    sym = self.all_symbols[symbol_id]
                    if sym.geo_object_type == geometry_type:
                        symbol_defs.append(sym)
                if self.detailed_print_outs:
                    print(f"build_symbols_for_layer({filter_string}) class_ids: {class_ids} symbol.count: {len(symbol_defs)}")
            else:
                class_ids = []

            doc = minidom.Document()

            #region "qgis" tag
            qgis = doc.createElement("qgis")
            qgis.setAttribute("simplifyDrawingHints", "1")
            qgis.setAttribute("symbologyReferenceScale", "-1")
            qgis.setAttribute("minScale", "100000000")
            qgis.setAttribute("maxScale", "0")
            qgis.setAttribute("version", "3.26.3-Buenos Aires")
            qgis.setAttribute("simplifyMaxScale", "1")
            qgis.setAttribute("readOnly", "0")
            qgis.setAttribute("labelsEnabled", "0")
            qgis.setAttribute("simplifyLocal", "1")
            qgis.setAttribute("simplifyDrawingTol", "1")
            qgis.setAttribute("styleCategories", "AllStyleCategories")
            qgis.setAttribute("simplifyAlgorithm", "0")
            qgis.setAttribute("hasScaleBasedVisibilityFlag", "0")
            #endregion

            #region "flags"
            flags = doc.createElement("flags")
            identifiable = doc.createElement("Identifiable")
            identifiable.appendChild(doc.createTextNode("1"))
            flags.appendChild(identifiable)
            removable = doc.createElement("Removable")
            removable.appendChild(doc.createTextNode("1"))
            flags.appendChild(removable)
            searchable = doc.createElement("Searchable")
            searchable.appendChild(doc.createTextNode("1"))
            flags.appendChild(searchable)
            private = doc.createElement("Private")
            private.appendChild(doc.createTextNode("0"))
            flags.appendChild(private)
            qgis.appendChild(flags)
            #endregion

            renderer = doc.createElement("renderer-v2")
            renderer.setAttribute("attr", "SymbolId")
            renderer.setAttribute("referencescale", "-1")
            renderer.setAttribute("type", "categorizedSymbol")
            renderer.setAttribute("enableorderby", "0")
            renderer.setAttribute("forceraster", "0")
            renderer.setAttribute("symbollevels", "0")

            #region "categories"
            categories = doc.createElement("categories")
            idx = 0
            for sym in symbol_defs:
                category = doc.createElement("category")
                category.setAttribute("symbol", str(idx))
                category.setAttribute("type", "long")
                category.setAttribute("label", str(sym.label))
                category.setAttribute("render", "true")
                category.setAttribute("value", str(sym.sym_id))
                categories.appendChild(category)
                #sym.symbol.setAttribute("type", sym.qml_sym_type)
                sym.idx = str(idx)
                idx += 1
            renderer.appendChild(categories)
            #endregion

            #region "symbols"
            symbols = doc.createElement("symbols")
            for sym in symbol_defs:
                #print(f"sym {sym})")

                symbol = doc.createElement("symbol")
                symbol.setAttribute("force_rhr", "0")
                symbol.setAttribute("frame_rate", "10")
                symbol.setAttribute("type", sym.qml_sym_type)
                symbol.setAttribute("name", sym.idx)
                symbol.setAttribute("alpha", "1")
                symbol.setAttribute("clip_to_extent", "1")
                symbol.setAttribute("is_animated", "0")

                layer = doc.createElement("layer")
                layer.setAttribute("locked", "0")
                layer.setAttribute("class", sym.get_class_type())
                layer.setAttribute("pass", "0")
                layer.setAttribute("enabled", "1")

                if sym.get_class_type() == "SimpleMarker":
                    option = self.create_simplemarker_option_tag(doc, sym)
                elif sym.get_class_type() == "FontMarker":
                    option = self.create_fontmarker_option_tag(doc, sym)
                elif sym.get_class_type() == "SimpleLine":
                    option = self.create_line_option_tag(doc, sym)
                elif sym.get_class_type() == "SimpleFill":
                    option = self.create_fill_option_tag(doc, sym)
                else:
                    option = self.create_simplemarker_option_tag(doc, sym)

                layer.appendChild(option)
                symbol.appendChild(layer)
                symbols.appendChild(symbol)
            renderer.appendChild(symbols)
            #endregion

            qgis.appendChild(renderer)

            #region "layerGeometryType"
            lyr_geom_type = doc.createElement("layerGeometryType")
            if sym.geo_object_type == GeometryType.Point:
                lyr_geom_type.appendChild(doc.createTextNode("0"))
            elif sym.geo_object_type == GeometryType.Polyline:
                lyr_geom_type.appendChild(doc.createTextNode("1"))
            elif sym.geo_object_type == GeometryType.Polygon:
                lyr_geom_type.appendChild(doc.createTextNode("2"))
            elif sym.geo_object_type == GeometryType.Multipoint:
                lyr_geom_type.appendChild(doc.createTextNode("3"))
            qgis.appendChild(lyr_geom_type)
            #endregion

            doc.appendChild(qgis)
            return doc.toprettyxml(indent =" ")

        # pylint: disable=broad-except
        except Exception as err:
            traceback.print_exc()
            print(f"Error in build_symbols_for_layer() {err}")

    def create_simplemarker_option_tag(self, doc:minidom.Document, sym:SymbolDef) -> minidom.Element:
        """Create the Option tag that holds the settings for the simplemarker symbol"""
        option = doc.createElement("Option")
        option.setAttribute("type", "Map")
        self.create_option_value_tag(doc, option, "angle", "0")
        self.create_option_value_tag(doc, option, "cap_style", "square")
        self.create_option_value_tag(doc, option, "color", SymbolColor.to_text(sym.color))
        self.create_option_value_tag(doc, option, "horizontal_anchor_point", "1")
        self.create_option_value_tag(doc, option, "joinstyle", "bevel")
        symbol_type = sym.get_marker_symbol_type()
        if symbol_type == PointSymbolStyle.NotSet or symbol_type == PointSymbolStyle.Circle:
            self.create_option_value_tag(doc, option, "name", "circle")
        elif symbol_type == PointSymbolStyle.Square:
            self.create_option_value_tag(doc, option, "name", "square")
        elif symbol_type == PointSymbolStyle.Diamond:
            self.create_option_value_tag(doc, option, "name", "diamond")
        elif symbol_type == PointSymbolStyle.Triangle:
            self.create_option_value_tag(doc, option, "name", "triangle")
        elif symbol_type == PointSymbolStyle.Cross:
            self.create_option_value_tag(doc, option, "name", "cross_fill")
        else:
            raise SymbolException(f"Unsuported marker symbol_type: {symbol_type}")
        self.create_option_value_tag(doc, option, "offset", "0,0")
        self.create_option_value_tag(doc, option, "offset_map_unit_scale")
        self.create_option_value_tag(doc, option, "offset_unit", "MM")
        self.create_option_value_tag(doc, option, "outline_color", SymbolColor.to_text(None))
        self.create_option_value_tag(doc, option, "outline_style", "solid")
        self.create_option_value_tag(doc, option, "outline_width", "0")
        self.create_option_value_tag(doc, option, "scale_method", "diameter")
        self.create_option_value_tag(doc, option, "size", SymbolDef.size_to_text(sym.size))
        self.create_option_value_tag(doc, option, "size_map_unit_scale")
        self.create_option_value_tag(doc, option, "size_unit", "Points")
        self.create_option_value_tag(doc, option, "vertical_anchor_point", "1")
        return option

    def create_fontmarker_option_tag(self, doc:minidom.Document, sym:SymbolDef) -> minidom.Element:
        """Create the Option tag that holds the settings for the font symbol"""
        option = doc.createElement("Option")
        option.setAttribute("type", "Map")
        self.create_option_value_tag(doc, option, "angle", "0")
        self.create_option_value_tag(doc, option, "chr", chr(sym.index))
        self.create_option_value_tag(doc, option, "color", SymbolColor.to_text(sym.color))
        self.create_option_value_tag(doc, option, "font", sym.font)
        self.create_option_value_tag(doc, option, "font_style", "Regular")
        self.create_option_value_tag(doc, option, "horizontal_anchor_point", "1")
        self.create_option_value_tag(doc, option, "joinstyle", "bevel")
        self.create_option_value_tag(doc, option, "offset", "0,0")
        self.create_option_value_tag(doc, option, "offset_map_unit_scale")
        self.create_option_value_tag(doc, option, "offset_unit", "MM")
        self.create_option_value_tag(doc, option, "outline_color", SymbolColor.to_text(None))
        self.create_option_value_tag(doc, option, "outline_width", "0")
        self.create_option_value_tag(doc, option, "outline_width_map_unit_scale")
        self.create_option_value_tag(doc, option, "outline_width_unit", "Points")
        self.create_option_value_tag(doc, option, "size", SymbolDef.size_to_text(sym.size))
        self.create_option_value_tag(doc, option, "size_map_unit_scale")
        self.create_option_value_tag(doc, option, "size_unit", "Points")
        self.create_option_value_tag(doc, option, "vertical_anchor_point", "1")
        return option

    def create_line_option_tag(self, doc:minidom.Document, sym:SymbolDef) -> minidom.Element:
        """Create the Option tag that holds the settings for the symbol"""
        option = doc.createElement("Option")
        option.setAttribute("type", "Map")
        self.create_option_value_tag(doc, option, "align_dash_pattern", "0")
        self.create_option_value_tag(doc, option, "capstyle", "square")
        self.create_option_value_tag(doc, option, "customdash", "5;2")
        self.create_option_value_tag(doc, option, "customdash_map_unit_scale")
        self.create_option_value_tag(doc, option, "customdash_unit", "MM")
        self.create_option_value_tag(doc, option, "dash_pattern_offset", "0,0")
        self.create_option_value_tag(doc, option, "dash_pattern_offset_map_unit_scale")
        self.create_option_value_tag(doc, option, "dash_pattern_offset_unit", "MM")
        self.create_option_value_tag(doc, option, "joinstyle", "bevel")
        self.create_option_value_tag(doc, option, "line_color", SymbolColor.to_text(sym.color))
        symbol_type = sym.get_line_symbol_style()
        if symbol_type == LineSymbolStyle.NotSet or symbol_type == LineSymbolStyle.Solid:
            self.create_option_value_tag(doc, option, "line_style", "solid")
        elif symbol_type == LineSymbolStyle.Dashed:
            self.create_option_value_tag(doc, option, "line_style", "dash")
        elif symbol_type == LineSymbolStyle.Dotted:
            self.create_option_value_tag(doc, option, "line_style", "dot")
        elif symbol_type == LineSymbolStyle.DashDot:
            self.create_option_value_tag(doc, option, "line_style", "dash dot")
        elif symbol_type == LineSymbolStyle.DashDotDot:
            self.create_option_value_tag(doc, option, "line_style", "dash dot dot")
        else:
            raise SymbolException(f"Unsuported line symbol_type: {symbol_type}")
        self.create_option_value_tag(doc, option, "line_width", SymbolDef.size_to_text(sym.size))
        self.create_option_value_tag(doc, option, "line_width_unit", "Points")
        self.create_option_value_tag(doc, option, "offset", "0,0")
        self.create_option_value_tag(doc, option, "offset_map_unit_scale")
        self.create_option_value_tag(doc, option, "offset_unit", "MM")
        self.create_option_value_tag(doc, option, "ring_filter", "0")
        self.create_option_value_tag(doc, option, "trim_distance_end", "0")
        self.create_option_value_tag(doc, option, "trim_distance_end_map_unit_scale")
        self.create_option_value_tag(doc, option, "trim_distance_end_unit", "MM")
        self.create_option_value_tag(doc, option, "trim_distance_start", "0")
        self.create_option_value_tag(doc, option, "trim_distance_start_map_unit_scale")
        self.create_option_value_tag(doc, option, "trim_distance_start_unit", "MM")
        self.create_option_value_tag(doc, option, "tweak_dash_pattern_on_corners", "0")
        self.create_option_value_tag(doc, option, "use_custom_dash", "0")
        self.create_option_value_tag(doc, option, "width_map_unit_scale")
        return option

    def create_fill_option_tag(self, doc:minidom.Document, sym:SymbolDef) -> minidom.Element:
        """Create the Option tag that holds the settings for the symbol"""
        option = doc.createElement("Option")
        option.setAttribute("type", "Map")
        self.create_option_value_tag(doc, option, "border_width_map_unit_scale")
        self.create_option_value_tag(doc, option, "color", SymbolColor.to_text(sym.color))
        self.create_option_value_tag(doc, option, "joinstyle", "bevel")
        self.create_option_value_tag(doc, option, "offset", "0,0")
        self.create_option_value_tag(doc, option, "offset_map_unit_scale")
        self.create_option_value_tag(doc, option, "offset_unit", "MM")
        self.create_option_value_tag(doc, option, "outline_color", SymbolColor.to_text(sym.border_color))
        self.create_option_value_tag(doc, option, "outline_style", "solid")
        self.create_option_value_tag(doc, option, "outline_width", SymbolDef.size_to_text(sym.border_width))
        self.create_option_value_tag(doc, option, "outline_width_unit", "Points")
        fill_style = sym.get_simple_fill_style()
        #print(f"sym_id: {sym.sym_id}  fill_style: {fill_style}   index: {sym.index}  sym_type: {sym.sym_type}")
        if fill_style == SimpleFillStyle.Solid:
            self.create_option_value_tag(doc, option, "style", "solid")
        elif fill_style == SimpleFillStyle.Hollow:
            self.create_option_value_tag(doc, option, "style", "no")
        elif fill_style == SimpleFillStyle.Horizontal:
            self.create_option_value_tag(doc, option, "style", "horizontal")
        elif fill_style == SimpleFillStyle.Vertical:
            self.create_option_value_tag(doc, option, "style", "vertical")
        elif fill_style == SimpleFillStyle.Cross:
            self.create_option_value_tag(doc, option, "style", "cross")
        elif fill_style == SimpleFillStyle.ForwardDiagonal:
            self.create_option_value_tag(doc, option, "style", "f_diagonal")
        elif fill_style == SimpleFillStyle.BackwardDiagonal:
            self.create_option_value_tag(doc, option, "style", "b_diagonal")
        elif fill_style == SimpleFillStyle.DiagonalCross:
            self.create_option_value_tag(doc, option, "style", "diagonal_x")
        else:
            self.create_option_value_tag(doc, option, "style", "solid")
        return option

    def create_option_value_tag(self, doc:minidom.Document, parent:minidom.Element, name:str, value:str = "3x:0,0,0,0,0,0", op_type:str = "QString") -> None:
        """Create single Option tag with attributes"""
        opt = doc.createElement("Option")
        opt.setAttribute("name", name)
        opt.setAttribute("type", op_type)
        opt.setAttribute("value", value)
        parent.appendChild(opt)

    def get_symbols_for_classes(self, class_ids:[int], geometry_type:GeometryType):
        """Get symbols for given classes and geometry type"""
        try:
            symbols = []
            if  geometry_type not in self.geometry_classes:
                return symbols

            for class_id, symbol_ids in self.class_symbol_ids.items():
                if class_id not in class_ids:
                    continue
                if self.detailed_print_outs:
                    print(f"ClassId: {class_id} symbol_ids.count: {len(symbol_ids)}  ({symbol_ids})")
                classes = self.geometry_classes[geometry_type]
                if class_id in classes:
                    symbols.extend(symbol_ids)
            return symbols
        except Exception:
            traceback.print_exc()

    def load_used_symbol_ids(self) -> None:
        """Load Used SymbolIds"""
        sql = Utils.load_resource('sql/select_used_symbols.sql')
        data_frame = pd.read_sql(sql, self.conn)
        self.class_symbol_ids = {}
        self.subclass_symbol_ids = {}
        for row in data_frame.itertuples(index=False):
            if row.ClassId not in self.class_symbol_ids:
                self.class_symbol_ids[row.ClassId] = [row.SymbolId]
            else:
                if row.SymbolId not in self.class_symbol_ids[row.ClassId]:
                    self.class_symbol_ids[row.ClassId].append(row.SymbolId)

            if row.SubClassId is not None:
                if row.SubClassId not in self.subclass_symbol_ids:
                    self.subclass_symbol_ids[row.SubClassId] = [row.SymbolId]
                else:
                    if row.SymbolId not in self.subclass_symbol_ids[row.SubClassId]:
                        self.subclass_symbol_ids[row.SubClassId].append(row.SymbolId)

    def load_class_geometries(self) -> None:
        """Load classes and there geometries"""
        try:
            sql = Utils.load_resource('sql/select_class_geometries.sql')
            data_frame = pd.read_sql(sql, self.conn)
            self.class_geometries = {}
            self.geometry_classes = {}
            for row in data_frame.itertuples(index=False):
                geom_type = GeometryType[row.Type]
                #print(f"ClassID: {row.ClassId}, Type: {geom_type}")
                #symbol_defs.append(SymbolDef(row))
                if row.ClassId in self.class_geometries:
                    self.class_geometries[row.ClassId].append(geom_type)
                else:
                    self.class_geometries[row.ClassId] = [geom_type]
                if geom_type in self.geometry_classes:
                    self.geometry_classes[geom_type].append(row.ClassId)
                else:
                    self.geometry_classes[geom_type] = [row.ClassId]
        except Exception:
            traceback.print_exc()

    def load_class_symbols(self) -> None:
        """Load symbols for all classes"""
        #try:
        sql = Utils.load_resource('sql/select_all_symbols.sql')
        data_frame = pd.read_sql(sql, self.conn)
        self.class_symbols = {}
        for row in data_frame.itertuples(index=False):
            symbol = SymbolDef(row)
            self.all_symbols[symbol.sym_id] = symbol
            if row.ClassId in self.class_symbols:
                self.class_symbols[row.ClassId].append(symbol)
            else:
                self.class_symbols[row.ClassId] = [symbol]

    def load_symbols_defs_for_layer(self, filter_string:str) -> [SymbolDef]:
        """Load symbol definitions from the database"""
        sql = Utils.load_resource("sql/symbol_query.sql")
        if filter_string != "":
            sql = sql.replace("GEOM_FILTER_STRING", f"geometrytype(the_geom) IN({filter_string})")
        else:
            sql = sql.replace("GEOM_FILTER_STRING", "the_geom is not NULL")
        data_frame = pd.read_sql(sql, self.conn)
        symbol_defs = []
        for row in data_frame.itertuples(index=False):
            symbol_defs.append(SymbolDef(row))
        return symbol_defs

    @staticmethod
    def wkb_type_to_layer(wkb_type:QgsWkbTypes) -> tuple[str,str]:
        """Convert wkbType to layer_name and filter_string"""
        layer_name = ""
        filter_string = ""
        if wkb_type == QgsWkbTypes.PointZM:
            layer_name = "Point"
            filter_string = "'POINT'"
        elif wkb_type == QgsWkbTypes.MultiPointZM:
            layer_name = "Multipoint"
            filter_string = "'MULTIPOINT'"
        elif wkb_type == QgsWkbTypes.MultiLineStringZM:
            layer_name = "Polyline"
            filter_string = "'LINESTRING','MULTILINESTRING'"
        elif wkb_type == QgsWkbTypes.MultiPolygonZM:
            layer_name = "Polygon"
            filter_string = "'POLYGON','MULTIPOLYGON'"
        else:
            raise SymbolException(f"Unknown wkb_type: {wkb_type}")
        return layer_name, filter_string

    @staticmethod
    def filter_string_to_gometry_type(filter_string:str) -> GeometryType:
        """Convert filter_string to GeometryType"""
        if filter_string == "'POINT'":
            return GeometryType.Point
        elif filter_string == "'MULTIPOINT'":
            return GeometryType.Multipoint
        elif filter_string == "'LINESTRING','MULTILINESTRING'":
            return GeometryType.Polyline
        elif filter_string == "'POLYGON','MULTIPOLYGON'":
            return GeometryType.Polygon
        return GeometryType.NotSet
