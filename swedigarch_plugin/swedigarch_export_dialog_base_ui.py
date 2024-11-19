# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'c:\Projects\swedigarch\swedigarch_plugin\swedigarch_export_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SwedigarchExportDialogBase(object):
    def setupUi(self, SwedigarchExportDialogBase):
        SwedigarchExportDialogBase.setObjectName("SwedigarchExportDialogBase")
        SwedigarchExportDialogBase.resize(939, 681)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("c:\\Projects\\swedigarch\\swedigarch_plugin\\assets/svedigark.svg"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        SwedigarchExportDialogBase.setWindowIcon(icon)
        SwedigarchExportDialogBase.setSizeGripEnabled(True)
        self.gridLayout_2 = QtWidgets.QGridLayout(SwedigarchExportDialogBase)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_db_conect = QtWidgets.QHBoxLayout()
        self.horizontalLayout_db_conect.setObjectName("horizontalLayout_db_conect")
        self.label_Server = QtWidgets.QLabel(SwedigarchExportDialogBase)
        self.label_Server.setObjectName("label_Server")
        self.horizontalLayout_db_conect.addWidget(self.label_Server)
        self.lineEdit_DbConnection = QtWidgets.QLineEdit(SwedigarchExportDialogBase)
        self.lineEdit_DbConnection.setMinimumSize(QtCore.QSize(280, 22))
        self.lineEdit_DbConnection.setMaximumSize(QtCore.QSize(500, 22))
        self.lineEdit_DbConnection.setReadOnly(True)
        self.lineEdit_DbConnection.setObjectName("lineEdit_DbConnection")
        self.horizontalLayout_db_conect.addWidget(self.lineEdit_DbConnection)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_db_conect.addItem(spacerItem)
        self.pgSelectConnection = QtWidgets.QPushButton(SwedigarchExportDialogBase)
        self.pgSelectConnection.setObjectName("pgSelectConnection")
        self.horizontalLayout_db_conect.addWidget(self.pgSelectConnection)
        self.pbConnect = QtWidgets.QPushButton(SwedigarchExportDialogBase)
        self.pbConnect.setMaximumSize(QtCore.QSize(80, 22))
        self.pbConnect.setObjectName("pbConnect")
        self.horizontalLayout_db_conect.addWidget(self.pbConnect)
        self.pbDisconnect = QtWidgets.QPushButton(SwedigarchExportDialogBase)
        self.pbDisconnect.setObjectName("pbDisconnect")
        self.horizontalLayout_db_conect.addWidget(self.pbDisconnect)
        self.verticalLayout_2.addLayout(self.horizontalLayout_db_conect)
        self.groupBoxSearch = QtWidgets.QGroupBox(SwedigarchExportDialogBase)
        self.groupBoxSearch.setMinimumSize(QtCore.QSize(0, 61))
        self.groupBoxSearch.setObjectName("groupBoxSearch")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.groupBoxSearch)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout_search = QtWidgets.QHBoxLayout()
        self.horizontalLayout_search.setObjectName("horizontalLayout_search")
        self.lineEditSearch = QtWidgets.QLineEdit(self.groupBoxSearch)
        self.lineEditSearch.setMaximumSize(QtCore.QSize(377, 16777215))
        self.lineEditSearch.setObjectName("lineEditSearch")
        self.horizontalLayout_search.addWidget(self.lineEditSearch)
        self.lblSearchInfo = QtWidgets.QLabel(self.groupBoxSearch)
        self.lblSearchInfo.setObjectName("lblSearchInfo")
        self.horizontalLayout_search.addWidget(self.lblSearchInfo)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_search.addItem(spacerItem1)
        self.verticalLayout_3.addLayout(self.horizontalLayout_search)
        self.verticalLayout_2.addWidget(self.groupBoxSearch)
        self.groupBoxDatabases = QtWidgets.QGroupBox(SwedigarchExportDialogBase)
        self.groupBoxDatabases.setMinimumSize(QtCore.QSize(0, 80))
        self.groupBoxDatabases.setStatusTip("")
        self.groupBoxDatabases.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.groupBoxDatabases.setFlat(False)
        self.groupBoxDatabases.setObjectName("groupBoxDatabases")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBoxDatabases)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.lwDatabases = QtWidgets.QListWidget(self.groupBoxDatabases)
        self.lwDatabases.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lwDatabases.setObjectName("lwDatabases")
        self.verticalLayout.addWidget(self.lwDatabases)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pbSelectAllDb = QtWidgets.QPushButton(self.groupBoxDatabases)
        self.pbSelectAllDb.setMinimumSize(QtCore.QSize(0, 24))
        self.pbSelectAllDb.setObjectName("pbSelectAllDb")
        self.horizontalLayout_2.addWidget(self.pbSelectAllDb)
        spacerItem2 = QtWidgets.QSpacerItem(12, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem2)
        self.pbAdd = QtWidgets.QPushButton(self.groupBoxDatabases)
        self.pbAdd.setMinimumSize(QtCore.QSize(0, 24))
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("c:\\Projects\\swedigarch\\swedigarch_plugin\\assets/arrow_down.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pbAdd.setIcon(icon1)
        self.pbAdd.setObjectName("pbAdd")
        self.horizontalLayout_2.addWidget(self.pbAdd)
        spacerItem3 = QtWidgets.QSpacerItem(12, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem3)
        self.pbRemove = QtWidgets.QPushButton(self.groupBoxDatabases)
        self.pbRemove.setMinimumSize(QtCore.QSize(0, 24))
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("c:\\Projects\\swedigarch\\swedigarch_plugin\\assets/arrow_up.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.pbRemove.setIcon(icon2)
        self.pbRemove.setObjectName("pbRemove")
        self.horizontalLayout_2.addWidget(self.pbRemove)
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem4)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout_4.addLayout(self.verticalLayout)
        self.verticalLayout_2.addWidget(self.groupBoxDatabases)
        self.groupBoxSelected = QtWidgets.QGroupBox(SwedigarchExportDialogBase)
        self.groupBoxSelected.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.groupBoxSelected.setObjectName("groupBoxSelected")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBoxSelected)
        self.gridLayout.setContentsMargins(4, 4, 4, 4)
        self.gridLayout.setObjectName("gridLayout")
        self.lwSelectedDatabases = QtWidgets.QListWidget(self.groupBoxSelected)
        self.lwSelectedDatabases.setStatusTip("")
        self.lwSelectedDatabases.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lwSelectedDatabases.setObjectName("lwSelectedDatabases")
        self.gridLayout.addWidget(self.lwSelectedDatabases, 0, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.groupBoxSelected)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(SwedigarchExportDialogBase)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.lineEditExportDirectory = QtWidgets.QLineEdit(SwedigarchExportDialogBase)
        self.lineEditExportDirectory.setObjectName("lineEditExportDirectory")
        self.horizontalLayout.addWidget(self.lineEditExportDirectory)
        self.pbBrowse = QtWidgets.QPushButton(SwedigarchExportDialogBase)
        self.pbBrowse.setMaximumSize(QtCore.QSize(25, 16777215))
        self.pbBrowse.setObjectName("pbBrowse")
        self.horizontalLayout.addWidget(self.pbBrowse)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.cbOverwriteExistingGeoPackage = QtWidgets.QCheckBox(SwedigarchExportDialogBase)
        self.cbOverwriteExistingGeoPackage.setObjectName("cbOverwriteExistingGeoPackage")
        self.horizontalLayout_3.addWidget(self.cbOverwriteExistingGeoPackage)
        self.cbExportCSV = QtWidgets.QCheckBox(SwedigarchExportDialogBase)
        self.cbExportCSV.setObjectName("cbExportCSV")
        self.horizontalLayout_3.addWidget(self.cbExportCSV)
        self.cbFilterSubClass = QtWidgets.QCheckBox(SwedigarchExportDialogBase)
        self.cbFilterSubClass.setObjectName("cbFilterSubClass")
        self.horizontalLayout_3.addWidget(self.cbFilterSubClass)
        self.cbSimplifiedExport = QtWidgets.QCheckBox(SwedigarchExportDialogBase)
        self.cbSimplifiedExport.setObjectName("cbSimplifiedExport")
        self.horizontalLayout_3.addWidget(self.cbSimplifiedExport)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem5)
        self.button_box = QtWidgets.QDialogButtonBox(SwedigarchExportDialogBase)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.button_box.setObjectName("button_box")
        self.horizontalLayout_3.addWidget(self.button_box)
        self.help_button = QtWidgets.QPushButton(SwedigarchExportDialogBase)
        self.help_button.setObjectName("help_button")
        self.horizontalLayout_3.addWidget(self.help_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.gridLayout_2.addLayout(self.verticalLayout_2, 0, 0, 1, 1)

        self.retranslateUi(SwedigarchExportDialogBase)
        self.button_box.accepted.connect(SwedigarchExportDialogBase.accept) # type: ignore
        self.button_box.rejected.connect(SwedigarchExportDialogBase.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(SwedigarchExportDialogBase)

    def retranslateUi(self, SwedigarchExportDialogBase):
        _translate = QtCore.QCoreApplication.translate
        SwedigarchExportDialogBase.setWindowTitle(_translate("SwedigarchExportDialogBase", "Intrasis DB Manager"))
        self.label_Server.setText(_translate("SwedigarchExportDialogBase", "Database connection"))
        self.pgSelectConnection.setToolTip(_translate("SwedigarchExportDialogBase", "Select stored PostgreSQL connection (stored by DB Manager)"))
        self.pgSelectConnection.setText(_translate("SwedigarchExportDialogBase", "Select connection"))
        self.pbConnect.setText(_translate("SwedigarchExportDialogBase", "Connect..."))
        self.pbDisconnect.setText(_translate("SwedigarchExportDialogBase", "Disconnect"))
        self.groupBoxSearch.setTitle(_translate("SwedigarchExportDialogBase", "Filter databases"))
        self.lblSearchInfo.setText(_translate("SwedigarchExportDialogBase", "search info text"))
        self.groupBoxDatabases.setToolTip(_translate("SwedigarchExportDialogBase", "Doubleclick to move databases between the lists"))
        self.groupBoxDatabases.setTitle(_translate("SwedigarchExportDialogBase", "Available databases"))
        self.lwDatabases.setToolTip(_translate("SwedigarchExportDialogBase", "Doubleclick to move databaases between lists"))
        self.pbSelectAllDb.setToolTip(_translate("SwedigarchExportDialogBase", "Add / remove all databases"))
        self.pbSelectAllDb.setText(_translate("SwedigarchExportDialogBase", "Select all databases"))
        self.pbAdd.setToolTip(_translate("SwedigarchExportDialogBase", "Add selected databases"))
        self.pbAdd.setText(_translate("SwedigarchExportDialogBase", "Add"))
        self.pbRemove.setToolTip(_translate("SwedigarchExportDialogBase", "Remove selected databases"))
        self.pbRemove.setText(_translate("SwedigarchExportDialogBase", "Remove"))
        self.groupBoxSelected.setToolTip(_translate("SwedigarchExportDialogBase", "Doubleclick to move databaases between lists"))
        self.groupBoxSelected.setTitle(_translate("SwedigarchExportDialogBase", "Selected databases for export"))
        self.lwSelectedDatabases.setToolTip(_translate("SwedigarchExportDialogBase", "Doubleclick to move databaases between lists"))
        self.label.setText(_translate("SwedigarchExportDialogBase", "Export catalog"))
        self.pbBrowse.setText(_translate("SwedigarchExportDialogBase", "…"))
        self.cbOverwriteExistingGeoPackage.setToolTip(_translate("SwedigarchExportDialogBase", "If the GeoPackage already exist it will be overwritten if checked.\n"
"Otherwice the GeoPackage will not be exported."))
        self.cbOverwriteExistingGeoPackage.setText(_translate("SwedigarchExportDialogBase", "Overwrite existing GeoPackage"))
        self.cbExportCSV.setToolTip(_translate("SwedigarchExportDialogBase", "Should an CSV export also be done for every exported database"))
        self.cbExportCSV.setText(_translate("SwedigarchExportDialogBase", "Export CSV"))
        self.cbFilterSubClass.setText(_translate("SwedigarchExportDialogBase", "Filter by SubClass"))
        self.cbSimplifiedExport.setToolTip(_translate("SwedigarchExportDialogBase", "Should an CSV export also be done for every exported database"))
        self.cbSimplifiedExport.setText(_translate("SwedigarchExportDialogBase", "Simplified Export"))
        self.help_button.setText(_translate("SwedigarchExportDialogBase", "Help"))
