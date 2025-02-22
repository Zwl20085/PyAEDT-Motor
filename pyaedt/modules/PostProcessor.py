"""
This module contains these classes: `FieldPlot`, `PostProcessor`, and `SolutionData`.

This module provides all functionalities for creating and editing plots in the 3D tools.

"""
from __future__ import absolute_import
import os
import shutil
import random
import string
import time
import math
import itertools
from collections import OrderedDict
from ..modeler.Modeler import CoordinateSystem
from ..generic.general_methods import aedt_exception_handler, generate_unique_name, retry_ntimes
from ..generic.filesystem import Scratch
from ..application.Variables import AEDT_units
import warnings
report_type = {"DrivenModal": "Modal Solution Data", "DrivenTerminal": "Terminal Solution Data",
               "Eigenmode": "EigenMode Parameters",
               "Transient Network": "Terminal Solution Data", "SBR+": "Modal Solution Data", "Transient": "Transient",
               "EddyCurrent": "EddyCurrent",
               "SteadyTemperatureAndFlow": "Monitor", "SteadyTemperatureOnly": "Monitor", "SteadyFlowOnly": "Monitor",
               "SteadyState": "Monitor", "NexximLNA": "Standard", "NexximDC": "Standard",
               "Magnetostatic": "Magnetostatic", "Electrostatic": "Electrostatic", "Circuit Design":"Standard",
               "NexximTransient": "Standard", "HFSS3DLayout": "Terminal Solution Data", "Matrix": "Matrix",
               "HFSS 3D Layout Design": "Standard", "Q3D Extractor": "Matrix", "2D Extractor": "Matrix"}


class SolutionData(object):
    """Contains information from the :func:`GetSolutionDataPerVariation` method."""
    @property
    def sweeps(self):
        """Sweeps."""
        return self._sweeps

    @property
    def sweeps_siunits(self):
        """SI units for the sweep."""
        data = {}
        for el in self._sweeps:
            data[el] = self._convert_list_to_SI(self._sweeps[el], self._quantity(self.units_sweeps[el]), self.units_sweeps[el])
        return data

    @property
    def variations_value(self):
        """Variation values for design variables."""
        vars = self.nominal_variation.GetDesignVariableNames()
        variationvals = {}
        for v in vars:
            variationvals[v] = self.nominal_variation.GetDesignVariableValue(v)
        return variationvals

    @property
    def nominal_variation(self):
        """Nominal variation."""
        return self._nominal_variation

    @nominal_variation.setter
    def nominal_variation(self, val):

        if 0 <= val <= self.number_of_variations:
            self._nominal_variation = self._original_data[val]
        else:
            print(str(val) + " not in Variations")

    @property
    def primary_sweep(self):
        """Primary sweep.

        Parameters
        ----------
        ps : float
            Perimeter of the source.
        """
        return self._primary_sweep

    @primary_sweep.setter
    def primary_sweep(self, ps):
        if ps in self.sweeps.keys():
            self._primary_sweep = ps

    @property
    def expressions(self):
        """Expressions."""
        mydata = [i for i in self._nominal_variation.GetDataExpressions()]
        return list(dict.fromkeys(mydata))

    def __init__(self, Data):
        self._original_data = Data
        self.number_of_variations = len(Data)
        self._nominal_variation = None
        self.nominal_variation = 0
        self._sweeps = None
        self._sweeps_names = list(self.nominal_variation.GetSweepNames())
        self.update_sweeps()

        self._primary_sweep = self._sweeps_names[0]
        self.nominal_sweeps = {}
        self.units_sweeps = {}
        for e in self.sweeps.keys():
            try:
                self.nominal_sweeps[e] = self.sweeps[e][0]
                self.units_sweeps[e] = self.nominal_variation.GetSweepUnits(e)
            except:
                self.nominal_sweeps[e] = None
        self.solutions_data_real = self._solution_data_real()
        self.solutions_data_imag = self._solution_data_imag()
        self.solutions_data_mag = {}
        self.units_data = {}
        for expr in self.expressions:
            self.solutions_data_mag[expr] = {}
            self.units_data[expr] = self.nominal_variation.GetDataUnits(expr)
            for i in self.solutions_data_real[expr]:
                self.solutions_data_mag[expr][i] = abs(
                    complex(self.solutions_data_real[expr][i], self.solutions_data_imag[expr][i]))

    @aedt_exception_handler
    def update_sweeps(self):
        """Update sweeps.

        Returns
        -------
        dict
            Updated sweeps.
        """

        self._sweeps = OrderedDict({})
        for el in self._sweeps_names:
            self._sweeps[el] = [i for i in self.nominal_variation.GetSweepValues(el, False)]
            self._sweeps[el] = list(dict.fromkeys(self._sweeps[el]))
        return self._sweeps

    @aedt_exception_handler
    def _quantity(self, unit):
        """

        Parameters
        ----------
        unit :


        Returns
        -------

        """
        for el in AEDT_units:
            keys_units = [i.lower() for i in list(AEDT_units[el].keys())]
            if unit.lower() in keys_units:
                return el
        return None

    @aedt_exception_handler
    def _solution_data_real(self):
        """ """
        sols_data = {}
        for expression in self.expressions:
            solution = list(self.nominal_variation.GetRealDataValues(expression,False))
            values = []
            for el in reversed(self._sweeps_names):
                values.append(self.sweeps[el])
            solution_Data = {}
            i = 0
            for t in itertools.product(*values):
                solution_Data[t] = solution[i]
                i += 1
            sols_data[expression] = solution_Data
        return sols_data

    def _solution_data_imag(self):
        """ """
        sols_data = {}
        for expression in self.expressions:
            try:
                solution = list(self.nominal_variation.GetImagDataValues(expression,False))
            except:
                solution = [0 for i in range(len(self.solutions_data_real[expression]))]
            values = []
            for el in reversed(self._sweeps_names):
                values.append(self.sweeps[el])
            solution_Data = {}
            i = 0
            for t in itertools.product(*values):
                solution_Data[t] = solution[i]
                i += 1
            sols_data[expression] = solution_Data
        return sols_data

    @aedt_exception_handler
    def to_degrees(self, input_list):
        """Convert an input list from radians to degrees.

        Parameters
        ----------
        input_list : list
            List of inputs in radians.

        Returns
        -------
        list
            List of inputs in degrees.

        """
        return [i*2*math.pi/360 for i in input_list]

    @aedt_exception_handler
    def to_radians(self, input_list):
        """Convert an input list from degrees to radians.

        Parameters
        ----------
        input_list : list
            List of inputs in degrees.

        Returns
        -------
        type
            List of inputs in radians.

        """
        return [i*360/(2*math.pi) for i in input_list]

    def data_magnitude(self, expression=None, convert_to_SI=False):
        """Retrieve the data magnitude of an expression.

        Parameters
        ----------
        expression : str, optional
            Name of the expression. The default is ``None``, in which case the
            first expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of data.

        """
        if not expression:
            expression = self.expressions[0]
        temp = []
        for it in self.nominal_sweeps:
            temp.append(self.nominal_sweeps[it])
        temp = list(reversed(temp))
        try:
            solution_Data = self.solutions_data_mag[expression]
            sol = []
            position = list(reversed(self._sweeps_names)).index(self.primary_sweep)
            for el in self.sweeps[self.primary_sweep]:
                temp[position]=el
                sol.append(solution_Data[tuple(temp)])
        except:
            sol = []
            position = list(reversed(self._sweeps_names)).index(self.primary_sweep)
            for el in self.sweeps[self.primary_sweep]:
                temp[position]=el
                sol.append(0)
        if convert_to_SI and self._quantity(self.units_data[expression]):
            sol = self._convert_list_to_SI(sol, self._quantity(self.units_data[expression]), self.units_data[expression])
        return sol

    @aedt_exception_handler
    def _convert_list_to_SI(self, datalist, dataunits, units):
        """Convert a data list to the SI unit system.

        Parameters
        ----------
        datalist : list
           List of data to convert.
        dataunits :

        units :


        Returns
        -------
        list
           List of the data converted to the SI unit system.

        """
        sol = datalist
        if dataunits in AEDT_units and units in AEDT_units[dataunits]:
            sol = [i * AEDT_units[dataunits][units] for i in datalist]
        return sol

    @aedt_exception_handler
    def data_db(self, expression=None, convert_to_SI=False):
        """Retrieve the data in the database for an expression.

        Parameters
        ----------
        expression : str, optional
            Name of the expression. The default is ``None``,
            in which case the first expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of the data in the database for the expression.

        """
        if not expression:
            expression = self.expressions[0]

        return [10*math.log10(i) for i in self.data_magnitude(expression,convert_to_SI)]

    def data_real(self, expression=None, convert_to_SI=False):
        """Retrieve the real part of the data for an expression.

        Parameters
        ----------
        expression : str, None
            Name of the expression. The default is ``None``,
            in which case the first expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of the real data for the expression.

        """
        if not expression:
            expression = self.expressions[0]
        temp = []
        for it in self.nominal_sweeps:
            temp.append(self.nominal_sweeps[it])
        temp = list(reversed(temp))
        try:
            solution_Data = self.solutions_data_real[expression]
            sol = []
            position = list(reversed(self._sweeps_names)).index(self.primary_sweep)
            for el in self.sweeps[self.primary_sweep]:
                temp[position]=el
                sol.append(solution_Data[tuple(temp)])
        except:
            sol = []
            position = list(reversed(self._sweeps_names)).index(self.primary_sweep)
            for el in self.sweeps[self.primary_sweep]:
                temp[position]=el
                sol.append(0)
        if convert_to_SI and self._quantity(self.units_data[expression]):
            sol = self._convert_list_to_SI(sol, self._quantity(self.units_data[expression]), self.units_data[expression])
        return sol

    def data_imag(self, expression=None, convert_to_SI=False):
        """Retrieve the imaginary part of the data for an expression.

        Parameters
        ----------
        expression : str, optional
            Name of the expression. The default is ``None``,
            in which case the first expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of the imaginary data for the expression.

        """
        if not expression:
            expression = self.expressions[0]
        temp = []
        for it in self.nominal_sweeps:
            temp.append(self.nominal_sweeps[it])
        temp = list(reversed(temp))
        try:
            solution_Data = self.solutions_data_imag[expression]
            sol = []
            position = list(reversed(self._sweeps_names)).index(self.primary_sweep)
            for el in self.sweeps[self.primary_sweep]:
                temp[position]=el
                sol.append(solution_Data[tuple(temp)])
        except:
            sol = []
            position = list(reversed(self._sweeps_names)).index(self.primary_sweep)
            for el in self.sweeps[self.primary_sweep]:
                temp[position]=el
                sol.append(0)
        if convert_to_SI and self._quantity(self.units_data[expression]):
            sol = self._convert_list_to_SI(sol, self._quantity(self.units_data[expression]), self.units_data[expression])
        return sol


class FieldPlot:
    """Creates and edits field plots.

    Parameters
    ----------
    oField :

    objlist : list
        List of objects.
    solutionName : str
        Name of the solution.
    quantityName : str
        Name of the plot or the name of the object.
    intrinsicList: dict, optional
        Name of the intrinsic dictionary. The default is ``{}``.

    """

    def __init__(self, oField, objlist, solutionName, quantityName, intrinsincList={}):
        self.oField = oField
        self.faceIndexes = objlist
        self.solutionName = solutionName
        self.quantityName = quantityName
        self.intrinsincList = intrinsincList
        self.objtype = "Surface"
        self.listtype = "FaceList"
        self.name = "Field_Plot"
        self.Filled = False
        self.IsoVal = "Fringe"
        self.SmoothShade = True
        self.AddGrid = False
        self.MapTransparency = True
        self.Refinement = 0
        self.Transparency = 0
        self.SmoothingLevel = 0
        self.ArrowUniform = True
        self.ArrowSpacing = 0
        self.MinArrowSpacing = 0
        self.MaxArrowSpacing = 0
        self.GridColor = [255, 255, 255]
        self.PlotIsoSurface = True
        self.PointSize = 1
        self.CloudSpacing = 0.5
        self.CloudMinSpacing = -1
        self.CloudMaxSpacing = -1

    @aedt_exception_handler
    def create(self):
        """Create a field plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        self.oField.CreateFieldPlot(self.surfacePlotInstruction, "Field")
        return True

    @aedt_exception_handler
    def update(self):
        """Update the field plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oField.ModifyFieldPlot(self.name, self.surfacePlotInstruction)

    @aedt_exception_handler
    def modify_folder(self):
        """Modify the field plot folder.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oField.SetFieldPlotSettings(self.plotFolder,
                                         [
                                             "NAME:FieldsPlotItemSettings",
                                             self.plotsettings])
        return True

    @aedt_exception_handler
    def delete(self):
        """Delete the field plot."""
        self.oField.DeleteFieldPlot([self.name])

    @property
    def plotFolder(self):
        """Field plot folder."""
        return self.name

    @property
    def plotGeomInfo(self):
        """Plot geometry information."""
        info = [1, self.objtype, self.listtype, 0]
        for index in self.faceIndexes:
            info.append(str(index))
            info[3] += 1
        return info

    @property
    def intrinsicVar(self):
        """Intrinsic variable.

        Returns
        -------
        list or dict
            List or dictionary of the variables for the field plot.
        """
        var = ""
        if type(self.intrinsincList) is list:
            l = 0
            while l < len(self.intrinsincList):
                val = self.intrinsincList[l + 1]
                if ":=" in self.intrinsincList[l] and type(self.intrinsincList[l+1]) is list:
                    val = self.intrinsincList[l + 1][0]
                ll=self.intrinsincList[l].split(":=")
                var += ll[0] + "=\'" + str(val) + "\' "
                l += 2
        else:
            for a in self.intrinsincList:
                var += a + "=\'" + str(self.intrinsincList[a]) + "\' "
        return var

    @property
    def plotsettings(self):
        """Plot settings.

        Returns
        -------
        list
            List of plot settings.
        """
        if self.objtype == "Surface":
            arg = [
                "NAME:PlotOnSurfaceSettings",
                "Filled:=", self.Filled,
                "IsoValType:=", self.IsoVal,
                "SmoothShade:=", self.SmoothShade,
                "AddGrid:=", self.AddGrid,
                "MapTransparency:=", self.MapTransparency,
                "Refinement:=", self.Refinement,
                "Transparency:=", self.Transparency,
                "SmoothingLevel:=", self.SmoothingLevel,
                [
                    "NAME:Arrow3DSpacingSettings",
                    "ArrowUniform:=", self.ArrowUniform,
                    "ArrowSpacing:=", self.ArrowSpacing,
                    "MinArrowSpacing:=", self.MinArrowSpacing,
                    "MaxArrowSpacing:=", self.MaxArrowSpacing
                ],
                "GridColor:=", self.GridColor
            ]
        else:
            arg = [
                "NAME:PlotOnVolumeSettings",
                "PlotIsoSurface:=", self.PlotIsoSurface,
                "PointSize:=", self.PointSize,
                "Refinement:=", self.Refinement,
                "CloudSpacing:=", self.CloudSpacing,
                "CloudMinSpacing:=", self.CloudMinSpacing,
                "CloudMaxSpacing:=", self.CloudMaxSpacing,
                [
                    "NAME:Arrow3DSpacingSettings",
                    "ArrowUniform:=", self.ArrowUniform,
                    "ArrowSpacing:=", self.ArrowSpacing,
                    "MinArrowSpacing:=", self.MinArrowSpacing,
                    "MaxArrowSpacing:=", self.MaxArrowSpacing
                ]
            ]
        return arg

    @property
    def surfacePlotInstruction(self):
        """Surface plot settings.

        Returns
        -------
        list
            List of surface plot settings.

        """
        return [
            "NAME:" + self.name,
            "SolutionName:=", self.solutionName,
            "QuantityName:=", self.quantityName,
            "PlotFolder:=", self.plotFolder,
            "UserSpecifyName:=", 0,
            "UserSpecifyFolder:=", 0,
            "StreamlinePlot:=", False,
            "AdjacentSidePlot:=", False,
            "FullModelPlot:=", False,
            "IntrinsicVar:=", self.intrinsicVar,
            "PlotGeomInfo:=", self.plotGeomInfo,
            "FilterBoxes:=", [0],
            self.plotsettings, "EnableGaussianSmoothing:=", False]


class PostProcessorCommon(object):
    """Manages the main AEDT postprocessing functions.

    The inherited `AEDTConfig` class contains all `_desktop` hierarchical calls
    needed for the class inititialization data `_desktop` and the design types ``"HFSS"``,
    ``"Icepak"``, and ``"HFSS3DLayout"``.

    .. note::
   Some functionalities are available only when AEDT is running in the graphical mode.

    Parameters
    ----------
    parent:
        Inherited parent object. The parent object must provide the members
        `_modeler`, `_desktop`, `_odesign`, and `_messenger`.

    """

    def __init__(self, parent):
        self._parent = parent
        self._scratch = Scratch(self._parent.temp_directory, volatile=True)

    @property
    def oreportsetup(self):
        """Report setup.

        Returns
        -------
        :attr:`pyaedt.modules.PostProcessor.PostProcessor.oreportsetup`

        """
        return self.odesign.GetModule("ReportSetup")

    @property
    def _messenger(self):
        """Messenger."""
        return self._parent._messenger

    @property
    def _desktop(self):
        """Desktop."""
        return self._parent._desktop

    @property
    def odesign(self):
        """Design."""
        return self._parent._odesign

    @property
    def oproject(self):
        """Project."""
        return self._parent._oproject

    @property
    def modeler(self):
        """Modeler."""
        return self._parent._modeler

    @property
    def oeditor(self):
        """Editor."""
        return self.modeler.oeditor

    @property
    def post_solution_type(self):
        """Design solution type.

        Return
        ------
        type
            Design solution type.
        """
        try:
            return self.odesign.GetSolutionType()
        except:
            return self._parent._design_type

    @aedt_exception_handler
    def copy_report_data(self, PlotName):
        """Copy report data as static data.

        Parameters
        ----------
        PlotName :
            Name of the report.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oreportsetup.CopyReportsData([PlotName])
        self.oreportsetup.PasteReports()
        return True

    @aedt_exception_handler
    def delete_report(self, PlotName):
        """Delete a field plot report.

        Parameters
        ----------
        PlotName : str
            Name of the field plot report.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oreportsetup.DeleteReports([PlotName])
        return True

    @aedt_exception_handler
    def rename_report(self, PlotName, newname):
        """Rename a plot.

        Parameters
        ----------
        PlotName : str
            Name of the plot.
        newname : str
            New name of the plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oreportsetup.RenameReport(PlotName, newname)
        return True

    @aedt_exception_handler
    def get_report_data(self, expression="dB(S(1,1))", setup_sweep_name='', domain='Sweep', families_dict=None,
                        report_input_type=None):
        """Generate report data.

        This method returns the data object and the arrays ``solData`` and
        ``FreqVals``.

        Parameters
        ----------
        expression : str or list
            One or more formulas to add to the report. The default is
            ``"dB(S(1,1))"``.
        setup_sweep_name : str, optional
            Name of the setup for computing the report. The
            default is ``""``, in which case the nominal sweep is
            used.
        domain : str or list, optional
            Context type. The options are ``"Sweep"`` or
            ``"Time"``. The default is ``"Sweep".``
        families_dict : dict, optional
            Dictionary of all families including the primary
            sweep. The default is ``{"Freq": ["All"]}``.
        report_input_type :  str
            Type of input data for the report.

        Returns
        -------
        :class:`pyaedt.modules.PostProcessor.SolutionData`

        Examples
        --------
        Generate a report with the default sweep and default variation.

        >>> hfss = HFSS()
        >>> hfss.post.get_report_data("S(1,1)")

        >>> m3d = Maxwell3D()
        >>> m3d.post.get_report_data("SurfaceLoss")   # Eddy Current examples
        >>> m3d.post.get_report_data("Wind(LoadA,LaodA)")    # TransientAnalsysis

        """
        if self.post_solution_type in ["3DLayout", "NexximLNA", "NexximTransient"]:
            if domain == "Sweep":
                did = 3
            else:
                did = 1
            ctxt = ["NAME:Context", "SimValueContext:=",
                    [did, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0, "IDIID", False, "1"]]
        elif isinstance(domain, list):
            ctxt = domain
        else:
            ctxt = ["Domain:=", domain]

        if not isinstance(expression, list):
            expression = [expression]
        if not setup_sweep_name:
            setup_sweep_name = self._parent.nominal_sweep

        if not report_input_type:
            report_input_type = report_type[self.post_solution_type]

        if families_dict is None:
            families_dict = {"Freq": ["All"]}

        solution_data = self.get_solution_data_per_variation(report_input_type, setup_sweep_name, ctxt, families_dict,
                                                             expression)

        if not solution_data:
            warnings.warn("No Data Available. Check inputs")
            return False
        return solution_data

    @aedt_exception_handler
    def create_rectangular_plot(self, expression="dB(S(1,1))", setup_sweep_name='', families_dict={"Freq": ["All"]},
                                primary_sweep_variable="Freq", context=None, plotname=None, plottype=None):
        """Create a 2D rectangular plot in AEDT.

        Parameters
        ----------
        expression : str or list, optional
            One or more formulas to add to the report. The default is value = ``"dB(S(1,1))"``.
        setup_sweep_name : str, optional
            Setup name with the sweep. The default is ``""``.
        families_dict : dict, optional
            Dictionary of all families including the primary sweep. The default is ``{"Freq": ["All"]}``.
        primary_sweep_variable : str, optional
            Name of the primary sweep. The default is ``"Freq"``.
        context : str, optional
            The default is ``None``.
        plotname : str, optional
            Name of the plot. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        ctxt = []
        if not setup_sweep_name:
            setup_sweep_name = self._parent.nominal_sweep
        if self.post_solution_type in ["HFSS 3D Layout Design", "NexximLNA", "NexximTransient"]:
            if "Freq" == primary_sweep_variable or "Freq" in list(families_dict.keys()):
                did = 3
            else:
                did = 1
            ctxt = ["NAME:Context", "SimValueContext:=",
                    [did, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0, "IDIID", False, "1"]]
        elif context:
            if type(context) is list:
                ctxt = context
            else:
                ctxt = ["Context:=", context]

        if not isinstance(expression, list):
            expression = [expression]
        if not setup_sweep_name:
            setup_sweep_name = self._parent.nominal_sweep
        if self.post_solution_type not in report_type:
            print("Solution not supported")
            return False
        if not plottype:
            modal_data = report_type[self.post_solution_type]
        else:
            modal_data = plottype
        if not plotname:
            plotname = generate_unique_name("Plot")
        families_input = []
        families_input.append(primary_sweep_variable + ":=")
        if not primary_sweep_variable in families_dict:
            families_input.append(["All"])
        elif isinstance(families_dict[primary_sweep_variable], list):
            families_input.append(families_dict[primary_sweep_variable])
        else:
            families_input.append([families_dict[primary_sweep_variable]])
        for el in families_dict:
            if el == primary_sweep_variable:
                continue
            families_input.append(el + ":=")
            if isinstance(families_dict[el], list):
                families_input.append(families_dict[el])
            else:
                families_input.append([families_dict[el]])

        self.oreportsetup.CreateReport(plotname, modal_data, "Rectangular Plot", setup_sweep_name, ctxt, families_input,
                                       ["X Component:=", primary_sweep_variable, "Y Component:=",
                                        expression])

        return True

    @aedt_exception_handler
    def get_solution_data_per_variation(self, soltype='Far Fields', setup_sweep_name='', ctxt=None,
                                        sweeps=None, expression=''):
        """Retrieve solution data for each variation.

        Parameters
        ----------
        soltype : str, optional
            Type of the solution. For example, ``"Far Fields"`` or ``"Modal Solution Data"``. The default
            is ``"Far Fields"``.
        setup_sweep_name : str, optional
            Name of the setup for computing the report. The default is ``""``,
            in which case ``"nominal adaptive"`` is used.
        ctxt : list, optional
            List of context variables. The default is ``None``.
        sweeps : dict, optional
            Dictionary of variables and values. The default is ``None``,
            in which case this list is used:
            ``{'Theta': 'All', 'Phi': 'All', 'Freq': 'All'}``.
        expression : str or list, optional
            One or more traces to include. The default is ``""``.

        Returns
        -------
        :class:`pyaedt.modules.PostProcessor.SolutionData`

        """
        if sweeps is None:
            sweeps = {'Theta': 'All', 'Phi': 'All', 'Freq': 'All'}
        if not ctxt:
            ctxt = []
        if not isinstance(expression, list):
            expression = [expression]
        if not setup_sweep_name:
            setup_sweep_name = self._parent.nominal_adaptive
        sweep_list = []
        for el in sweeps:
            sweep_list.append(el + ":=")
            if type(sweeps[el]) is list:
                sweep_list.append(sweeps[el])
            else:
                sweep_list.append([sweeps[el]])

        data = self.oreportsetup.GetSolutionDataPerVariation(soltype, setup_sweep_name, ctxt, sweep_list, expression)
        return SolutionData(data)

    @aedt_exception_handler
    def steal_focus_oneditor(self):
        """Remove the selection of an object that would prevent the image from exporting correctly.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self._desktop.RestoreWindow()
        param = ["NAME:SphereParameters", "XCenter:=", "0mm", "YCenter:=", "0mm", "ZCenter:=", "0mm", "Radius:=", "1mm"]
        attr = ["NAME:Attributes", "Name:=", "DUMMYSPHERE1", "Flags:=", "NonModel#"]
        self.oeditor.CreateSphere(param, attr)
        self.oeditor.Delete(["NAME:Selections", "Selections:=", "DUMMYSPHERE1"])
        return True

    @aedt_exception_handler
    def export_report_to_csv(self, project_dir, plot_name):
        """Export the SParameter plot data to a CSV file.

        This method leaves the data in the plot (as data) as a reference
        for the Sparameters plot after the loops.

        Parameters
        ----------
        project_dir : str
            Path to the project directory.
        plot_name : str
            Name of the plot to export.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        npath = os.path.normpath(project_dir)

        csv_file_name = os.path.join(npath, plot_name + ".csv")
        self.oreportsetup.ExportToFile(plot_name, csv_file_name)
        return True

    @aedt_exception_handler
    def export_report_to_jpg(self, project_dir, plot_name):
        """Export the SParameter plot to a JPG file.

        Parameters
        ----------
        project_dir : str
            Path to the project directory.
        plot_name : str
            Name of the plot to export.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        # path
        npath = os.path.normpath(project_dir)
        file_name = os.path.join(npath, plot_name + ".jpg")  # name of the image file
        self.oreportsetup.ExportImageToFile(plot_name, file_name, 0, 0)
        return True


class PostProcessor(PostProcessorCommon, object):
    """Manages the main AEDT postprocessing functions.

    The inherited `AEDTConfig` class contains all `_desktop` hierarchical calls
    needed for the class inititialization data `_desktop` and the design types ``"HFSS"``,
    ``"Icepak"``, and ``"HFSS3DLayout"``.

    .. note::
   Some functionalities are available only when AEDT is running in the graphical mode.

    Parameters
    ----------
    parent:
        Inherited parent object. The parent object must provide the members
        `_modeler`, `_desktop`, `_odesign`, and `_messenger`.

    """

    def __init__(self, parent):
        self._parent = parent
        self.FieldsPlot = {}
        PostProcessorCommon.__init__(self, parent)

    @property
    def _primitives(self):
        """Primitives.

        Returns
        -------
        :class:`pyaedt.modeler.Primitives`
            Primitives object.

        """
        return self._parent._modeler.primitives

    @property
    def model_units(self):
        """Model units.

        Returns
        -------
        str
           Model units, such as ``"mm"``.
        """
        return retry_ntimes(10, self.oeditor.GetModelUnits)

    @property
    def post_osolution(self):
        """Solution.

        Returns
        -------
        type
            Solution module.
        """
        return self.odesign.GetModule("Solutions")

    @property
    def ofieldsreporter(self):
        """Fields reporter.

        Returns
        -------
        :attr:`pyaedt.modules.PostProcessor.PostProcessor.ofieldsreporter`

        """
        return self.odesign.GetModule("FieldsReporter")

    @property
    def report_types(self):
        """Report types."""
        return list(self.oreportsetup.GetAvailableReportTypes())

    @aedt_exception_handler
    def display_types(self, report_type):
        """Retrieve display types for a report type.

        Parameters
        ----------
        report_type : str
            Type of the report.

        Returns
        -------
        :attr:`pyaedt.modules.PostProcessor.PostProcessor.report_types`

        """
        return self.oreportsetup.GetAvailableDisplayTypes(report_type)

    # TODO: define a fields calculator module and make robust !!
    @aedt_exception_handler
    def volumetric_loss(self, object_name):
        """Use the field calculator to create a variable for volumetric losses.

        Parameters
        ----------
        object_name : str
            Name of the object to compute volumetric losses on.

        Returns
        -------
        str
            Name of the variable created.

        """
        oModule = self.ofieldsreporter
        oModule.EnterQty("OhmicLoss")
        oModule.EnterVol(object_name)
        oModule.CalcOp("Integrate")
        name = "P_{}".format(object_name)  # Need to check for uniqueness !
        oModule.AddNamedExpression(name, "Fields")
        return name

    @aedt_exception_handler
    def change_field_property(self,plotname, propertyname, propertyval):
        """Modify a field plot property.

        Parameters
        ----------
        plotname : str
            Name of the field plot.
        propertyname : str
            Name of the property.
        propertyval :
            Value for the property.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.odesign.ChangeProperty([
            "NAME:AllTabs",
            [
                "NAME:FieldsPostProcessorTab",
                [
                    "NAME:PropServers",
                    "FieldsReporter:"+plotname
                ],
                [
                    "NAME:ChangedProps",
                    [
                        "NAME:"+propertyname,
                        "Value:="	, propertyval
                    ]
                ]
            ]
        ])

    @aedt_exception_handler
    def export_field_file_on_grid(self, quantity_name, solution=None, variation_dict=None, filename=None,
                                  gridtype="Cartesian", grid_center=[0, 0, 0],
                                  grid_start=[0, 0, 0], grid_stop=[0, 0, 0], grid_step=[0, 0, 0], isvector = False, intrinsics=None, phase=None):
        """Use the field calculator to create a field file on a grid based on a solution and variation.

        Parameters
        ----------
        quantity_name : str
            Name of the quantity to export. For example, ``"Temp"``.
        solution : str, optional
            Name of the solution in the format ``"solution : sweep"``. The default is ``None``.
        variation_dict : dict, optional
            Dictionary of all variation variables with their values.
            The default is ``None``.
        filename : str, optional
            Full path and name to save the file to.
            The default is ``None``.
        gridtype : str, optional
            Type of the grid to export. The default is ``"Cartesian"``.
        grid_center : list, optional
            The ``[x, y, z]`` coordinates for the center of the grid.
            The default is ``[0, 0, 0]``. This parameter is disabled if ``gridtype=
            "Cartesian"``.
        grid_start : list, optional
            The ``[x, y, z]`` coordinates for the starting point of the grid.
            The default is ``[0, 0, 0]``.
        grid_stop : list, optional
            The ``[x, y, z]`` coordinates for the stopping point of the grid.
            The default is ``[0, 0, 0]``.
        grid_step : list, optional
            The ``[x, y, z]`` coordinates for the step size of the grid.
            The default is ``[0, 0, 0]``.
        isvector : bool, optional
            Whether the quantity is a vector. The  default is ``False``.
        intrinsics : str, optional
            This parameter is mandatory for a frequency field
            calculation. The default is ``None``.
        phase : str, optional
            Field phase. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self._messenger.add_info_message("Exporting {} field. Be patient".format(quantity_name))
        if not solution:
            solution = self._parent.existing_analysis_sweeps[0]
        if not filename:
            appendix = ""
            ext = ".fld"
            filename = os.path.join(self._parent.project_path, solution.replace(" : ", "_") + appendix + ext)
        else:
            filename = filename.replace("//", "/").replace("\\", "/")
        self.ofieldsreporter.CalcStack("clear")
        if isvector:
            self.ofieldsreporter.EnterQty(quantity_name)
            self.ofieldsreporter.CalcOp("Smooth")
            self.ofieldsreporter.EnterScalar(0)
            self.ofieldsreporter.CalcOp("AtPhase")
            self.ofieldsreporter.CalcOp("Mag")
        else:
            self.ofieldsreporter.EnterQty(quantity_name)
        obj_list = "AllObjects"
        self.ofieldsreporter.EnterVol(obj_list)
        self.ofieldsreporter.CalcOp("Mean")
        units=self.modeler.model_units
        ang_units="deg"
        if gridtype == "Cartesian":
            grid_center =["0mm", "0mm", "0mm"]
            grid_start_wu = [str(i)+units for i in grid_start]
            grid_stop_wu = [str(i)+units for i in grid_stop]
            grid_step_wu = [str(i)+units for i in grid_step]
        elif gridtype == "Cylinidrical":
            grid_center = [str(i)+units for i in grid_center]
            grid_start_wu = [str(grid_start[0])+units, str(grid_start[1])+ang_units, str(grid_start[2])+units]
            grid_stop_wu = [str(grid_stop[0])+units, str(grid_stop[1])+ang_units, str(grid_stop[2])+units]
            grid_step_wu = [str(grid_step[0])+units, str(grid_step[1])+ang_units, str(grid_step[2])+units]
        elif gridtype == "Spherical":
            grid_center = [str(i)+units for i in grid_center]
            grid_start_wu = [str(grid_start[0])+units, str(grid_start[1])+ang_units, str(grid_start[2])+ang_units]
            grid_stop_wu = [str(grid_stop[0])+units, str(grid_stop[1])+ang_units, str(grid_stop[2])+ang_units]
            grid_step_wu = [str(grid_step[0])+units, str(grid_step[1])+ang_units, str(grid_step[2])+ang_units]
        else:
            self._parent._messenger.add_error_message("Error in the type of the grid.")
            return False
        if not variation_dict:
            variation_dict = self._parent.available_variations.nominal_w_values
        if intrinsics:
            if "Transient" in solution:
                variation_dict.append("Time:=")
                variation_dict.append(intrinsics)
            else:
                variation_dict.append("Freq:=")
                variation_dict.append(intrinsics)
                variation_dict.append("Phase:=")
                if phase:
                    variation_dict.append(phase)
                else:
                    variation_dict.append("0deg")

        self.ofieldsreporter.ExportOnGrid(filename, grid_start_wu,
                                          grid_stop_wu, grid_step_wu,
                                          solution,
                                          variation_dict, True, gridtype, grid_center, False)
        return os.path.exists(filename)

    @aedt_exception_handler
    def export_field_file(self, quantity_name, solution=None, variation_dict=None, filename=None,
                          obj_list="AllObjects", obj_type="Vol", intrinsics=None, phase=None,
                          sample_points_file=None, sample_points_lists=None, export_with_sample_points=True):
        """Use the field calculator to create a field file based on a solution and variation.

        Parameters
        ----------
        quantity_name :
            Name of the quantity to export. For example, ``"Temp"``.
        solution : str, optional
            Name of the solution in the format ``"solution: sweep"``.
            The default is ``None``.
        variation_dict : dict, optional
            Dictionary of all variation variables with their values.
            The default is ``None``.
        filename : str, optional
            Full path and name to save the file to.
            The default is ``None``.
        obj_list : str, optional
            List of objects to export. The default is ``"AllObjects"``.
        obj_type : str, optional
            Type of objects to export. Options are ``"Vol"`` for volume and
            ``"Surf"`` for surface. The default is ``"Vol"``.
        intrinsics : str, optional
            This parameter is mandatory for a frequency or transient field
            calculation. The default is ``None``.
        phase : str, optional
            Field phase. The default is ``None``.
        sample_points_file : str, optional
            Name of the file with sample points. The default is ``None``.
        sample_points_lists : list, optional
            List of the sample points. The default is ``None``.
        export_with_sample_points : bool, optional
            Whether to include the sample points in the file to export.
            The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self._messenger.add_info_message("Exporting {} field. Be patient".format(quantity_name))
        if not solution:
            solution = self._parent.existing_analysis_sweeps[0]
        if not filename:
            appendix = ""
            ext = ".fld"
            filename = os.path.join(self._parent.project_path, solution.replace(" : ","_") + appendix + ext)
        else:
            filename = filename.replace("//", "/").replace("\\", "/")
        self.ofieldsreporter.CalcStack("clear")
        self.ofieldsreporter.EnterQty(quantity_name)

        if not variation_dict:
            if not sample_points_file and not sample_points_lists:
                if obj_type == "Vol":
                    self.ofieldsreporter.EnterVol(obj_list)
                elif obj_type == "Surf":
                    self.ofieldsreporter.EnterSurf(obj_list)
                else:
                    self._messenger.add_error_message("No correct choice.")
                    return False
                self.ofieldsreporter.CalcOp("Value")
                variation_dict = self._parent.available_variations.nominal_w_values
            else:
                variations = self._parent.available_variations.nominal_w_values_dict
                variation_dict = []
                for el, value in variations.items():
                    variation_dict.append(el+":=")
                    variation_dict.append(value)
        if intrinsics:
            if "Transient" in solution:
                variation_dict.append("Time:=")
                variation_dict.append(intrinsics)
            else:
                variation_dict.append("Freq:=")
                variation_dict.append(intrinsics)
                variation_dict.append("Phase:=")
                if phase:
                    variation_dict.append(phase)
                else:
                    variation_dict.append("0deg")
        if not sample_points_file and not sample_points_lists:

            self.ofieldsreporter.CalculatorWrite(filename, ["Solution:="	, solution], variation_dict)
        elif sample_points_file:

            self.ofieldsreporter.ExportToFile(filename, sample_points_file, solution, variation_dict, export_with_sample_points)
        else:
            sample_points_file = os.path.join(self._parent.project_path, "temp_points.pts")
            with open(sample_points_file, "w") as f:
                for point in sample_points_lists:
                    f.write(" ".join([str(i) for i in point])+"\n")
            self.ofieldsreporter.ExportToFile(filename, sample_points_file, solution, variation_dict, export_with_sample_points)

        return os.path.exists(filename)

    @aedt_exception_handler
    def export_field_plot(self, plotname, filepath, filename=""):
        """Export a field plot.

        Parameters
        ----------
        plotname : str
            Name of the plot.

        filepath : str
            Path for saving the file.

        filename : str, optional
            Name of the file. The default is ``""``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not filename:
            filename = plotname
        self.ofieldsreporter.ExportFieldPlot(plotname, False, os.path.join(filepath, filename + ".aedtplt"))
        return os.path.join(filepath, filename+".aedtplt")

    @aedt_exception_handler
    def _create_fieldplot(self, objlist, quantityName, setup_name, intrinsincList, objtype, listtype):
        """Internal function.

        Parameters
        ----------
        objlist : list
            List of fields to plot.
        quantityName : str
            Name of the field plot.
        setup_name :
            Name of the setup in the format ``"setupName : sweepName"``.
        intrinsincList :

        objtype :

        listtype :


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not setup_name:
            setup_name = self._parent.existing_analysis_sweeps[0]
        self._desktop.CloseAllWindows()
        self.oproject.SetActiveDesign(self._parent.design_name)
        try:
            self.oeditor.FitAll()
        except:
            self.oeditor.ZoomToFit()
        char_set = string.ascii_uppercase + string.digits
        uName = quantityName + '_' + ''.join(random.sample(char_set, 6))
        plot = FieldPlot(self.ofieldsreporter, objlist, setup_name, quantityName, intrinsincList)
        plot.name = uName
        plot.objtype = objtype
        plot.listtype = listtype
        plt = plot.create()
        if plt:
            self.FieldsPlot[uName] = plot
            return plot
        else:
            return False

    @aedt_exception_handler
    def create_fieldplot_surface(self, objlist, quantityName, setup_name=None, intrinsincDict={}):
        """Create a field plot of surfaces.

        Parameters
        ----------
        objlist : list
            List of surfaces to plot.
        quantityName : str
            Name of the quantity to plot.
        setup_name : str, optional
            Name of the setup in the format ``"setupName : sweepName"``. The default
            is ``None``.
        intrinsincDict : dict, optional
            Dictionary containing all intrinsic variables. The default
            is ``{}``.

        Returns
        -------
        type
            Plot object.

        """
        return self._create_fieldplot(objlist, quantityName, setup_name, intrinsincDict, "Surface", "FacesList")

    @aedt_exception_handler
    def create_fieldplot_cutplane(self, objlist, quantityName, setup_name=None, intrinsincDict={}):
        """Create a field plot of cut planes.

        Parameters
        ----------
        objlist : list
            List of cut planes to plot.
        quantityName : str
            Name of the quantity to plot.
        setup_name : str, optional
            Name of the setup in the format
            ``"setupName : sweepName"``. The default is ``None``,
            in which case ``"nominal, lastadaptive"`` is used.
        intrinsincDict : dict, optional
            Dictionary containing all intrinsic variables.
            The default is ``{}``.

        Returns
        -------
        type
            Plot object.

        """
        return self._create_fieldplot(objlist, quantityName, setup_name, intrinsincDict, "Surface", "CutPlane")

    @aedt_exception_handler
    def create_fieldplot_volume(self, objlist, quantityName, setup_name=None, intrinsincDict={}):
        """Create a field plot of volumes.

        Parameters
        ----------
        objlist : list
            List of volumes to plot.
        quantityName :
            Name of the quantity to plot.
        setup_name : str, optional
            Name of the setup in the format
            ``"setupName : sweepName"``. The default is ``None``,
            in which case ``"nominal, lastadaptive"`` is used.
        intrinsincDict : dict, optional
            Dictionary containing all intrinsic variables. The default
            is ``{}``.

        Returns
        -------
        type
            Plot object
        """
        return self._create_fieldplot(objlist, quantityName, setup_name, intrinsincDict, "Volume", "ObjList")

    @aedt_exception_handler
    def export_field_jpg(self, fileName, plotName, coordinateSystemName):
        """Export a field plot and coordinate system to a JPG file.

        Parameters
        ----------
        fileName : str
            Full path and name to save the JPG file to.
        plotName : str
            Name of the plot.
        coordinateSystemName :str
            Name of the coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        time.sleep(2)

        self.ofieldsreporter.ExportPlotImageToFile(fileName, "", plotName, coordinateSystemName)
        return True

    @aedt_exception_handler
    def export_field_image_with_View(self, plotName, exportFilePath, view="iso", wireframe=True):
        """Export a field plot image with a view.

        .. note::
           For AEDT 2019 R3, this method works only on the ISO view due to a bug in the API.
           This method works properly in 2021 R1.

        Parameters
        ----------
        plotName : str
            Name of the plot.
        exportFilePath :
            Path for exporting the image file.
        view : str, optional
            View to export. Options are ``"iso"``, ``"XZ"``, ``"XY"``, and ``"YZ"``.
            The default is ``"iso"``.
        wireframe : bool, optional
            Whether to put the objects in the wireframe mode. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        bound = self.modeler.get_model_bounding_box()
        center = [(float(bound[0]) + float(bound[3])) / 2,
                  (float(bound[1]) + float(bound[4])) / 2,
                  (float(bound[2]) + float(bound[5])) / 2]
        coordinateSystemForExportPlot = self.modeler.create_coordinate_system(origin=center, mode='view', view=view)
        wireframes = []
        if wireframe:
            names = self._primitives.object_names
            for el in names:
                if not self._primitives[el].display_wireframe:
                    wireframes.append(el)
                    self._primitives[el].display_wireframe = True
        status = self.export_field_jpg(exportFilePath, plotName, coordinateSystemForExportPlot.name)
        for solid in wireframes:
            self._primitives[solid].display_wireframe = False
        coordinateSystemForExportPlot.delete()
        return status

    @aedt_exception_handler
    def delete_field_plot(self, name):
        """Delete a field plot.

        Parameters
        ----------
        name : str
            Name of the field plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oreportsetup.DeleteFieldPlot([name])
        self.FieldsPlot.pop(name, None)
        return True

    @aedt_exception_handler
    def export_model_picture(self, dir=None, name=None, picturename=None, show_axis=True, show_grid=True, show_ruler=True):
        """Export a snapshot of the model to a JPG file.

        .. note::
           This method works only when AEDT is running in the graphical mode.

        Parameters
        ----------
        dir : str, optional
            Path for exporting the JPG file. The default is ``None``, in which case
            an internal volatile scratch in the ``temp`` directory is used.
        name : str, optional
            Name of the project, which is used to compose the directory path.
        picturename : str, optional
            Name of the JPG file. The default is ``None``, in which case the default
            name is assigned. The extension ``".jpg"`` is added automatically.
        show_axis : bool, optional
            Whether to show the axes. The default is ``True``.
        show_grid : bool, optional
            Whether to show the grid. The default is ``True``.
        show_ruler : bool, optional
            Whether to show the ruler. The default is ``True``.

        Returns
        -------
        str
            File path of the generated JPG file.
        """
        # Set up arguments list for createReport function
        if not dir:
            dir = self._scratch.path
            self._messenger.logger.debug("Using scratch path {}".format(self._scratch.path))

        assert os.path.exists(dir), "Specified directory does not exist: {}".format(dir)

        if name:
            project_subdirectory = os.path.join(dir, name)
            if not os.path.exists(project_subdirectory):
                os.mkdir(project_subdirectory)
            file_path = os.path.join(project_subdirectory, "Pictures")
            if not os.path.exists(file_path):
                os.mkdir(file_path)
        else:
            file_path = dir

        if not picturename:
            picturename = generate_unique_name("image")
        else:
            if picturename.endswith(".jpg"):
                picturename = picturename[:-4]

        # open the 3D modeler and remove the selection on other objects
        self.oeditor.ShowWindow()
        self.steal_focus_oneditor()
        self.oeditor.FitAll()
        # export the image
        arg = ["NAME:SaveImageParams", "ShowAxis:=", show_axis, "ShowGrid:=", show_grid, "ShowRuler:=", show_ruler,
               "ShowRegion:=", "Default", "Selections:=", ""]
        file_name = os.path.join(file_path, picturename + ".jpg")
        self.oeditor.ExportModelImageToFile(file_name, 0, 0, arg)
        return file_name

    @aedt_exception_handler
    def get_far_field_data(self, expression="GainTotal", setup_sweep_name='', domain="Infinite Sphere1", families_dict=None):
        """Generate far field data using the :func:`GetSolutionDataPerVariation` method.

        This method returns the data ``solData``, ``ThetaVals``, ``PhiVals``, ``ScanPhiVals``,
        ``ScanThetaVals``, and ``FreqVals``.

        Parameters
        ----------
        expression : str or list, optional
            One or more formulas to add to the report. The default is ``"GainTotal"``.
        setup_sweep_name : str, optional
            Name of the setup for computing the report. The default is ``""``,
            in which case the nominal sweep is used.
        domain : str, optional
            Context type (sweep or time). The default is ``"Infinite Sphere1"``.
        families_dict : dict, optional
            Dictionary of variables and values. The default is ``{"Freq": ["All"]}``.

        Returns
        -------
        :class:`pyaedt.modules.PostProcessor.SolutionData`

        """
        if type(expression) is not list:
            expression = [expression]
        if not setup_sweep_name:
            setup_sweep_name = self._parent.nominal_adaptive
        if families_dict is None:
            families_dict = {"Theta": ["All"], "Phi": ["All"], "Freq": ["All"]}
        solution_data = self.get_solution_data_per_variation("Far Fields", setup_sweep_name, ['Context:=', domain], families_dict, expression)
        if not solution_data:
            print("No Data Available. Check inputs")
            return False
        return solution_data


class CircuitPostProcessor(PostProcessorCommon, object):
    """Manages the main AEDT Nexxim postprocessing functions.


    .. note::
       Some functionalities are available only when AEDT is running in the graphical mode.

    Parameters
    ----------
    parent:
        Inherited parent object. The parent object must provide the members
        `_modeler`, `_desktop`, `_odesign`, and `_messenger`.

    """

    def __init__(self, parent):
        PostProcessorCommon.__init__(self, parent)

    def create_ami_initial_response_plot(self, setupname, ami_name, variation_list_w_value,
                                         plot_type="Rectangular Plot", plot_initial_response=True,
                                         plot_intermediate_response=False, plot_final_response=False, plotname=None):
        """Create an AMI initial response plot.


        Parameters
        ----------
        setupname: str
            Name of the setup
        ami_name: str
            AMI Probe name to use
        variation_list_w_value: list
            list of variations with relative values
        plot_type: str, Default ``"Rectangular Plot"``
            String containing the report type. Default is ``"Rectangular Plot"``. It can be ``"Data Table"``,
            ``"Rectangular Stacked Plot"``or any of the other valid AEDT Report types.
        plot_initial_response: bool, optional
            Set either to plot the initial input response.  Default is ``True``.
        plot_intermediate_response: bool, optional
            Set whether to plot the intermediate input response.  Default is ``False``.
        plot_final_response: bool, optional
            Set whether to plot the final input response.  Default is ``False``.
        plotname: str, optional
            The plot name.  Default is a unique name.

        Returns
        -------
        str
            Name of the plot.
        """
        if not plotname:
            plotname = generate_unique_name("AMIAnalysis")
        variations = [ "__InitialTime:=", ["All"]]
        i = 0
        for a in variation_list_w_value:
            if (i % 2) == 0:
                if ":=" in a:
                    variations.append(a)
                else:
                    variations.append(a + ":=")
            else:
                if isinstance(a, list):
                    variations.append(a)
                else:
                    variations.append([a])
            i += 1
        ycomponents = []
        if plot_initial_response:
            ycomponents.append("InitialImpulseResponse<{}.int_ami_rx>".format(ami_name))
        if plot_intermediate_response:
            ycomponents.append("IntermediateImpulseResponse<{}.int_ami_rx>".format(ami_name))
        if plot_final_response:
            ycomponents.append("FinalImpulseResponse<{}.int_ami_rx>".format(ami_name))
        self.oreportsetup.CreateReport(plotname, "Standard", plot_type, setupname, ["NAME:Context", "SimValueContext:=",
                                                                                    [55824, 0, 2, 0, False, False, -1,
                                                                                     1, 0, 1, 1, "", 0, 0, "NUMLEVELS",
                                                                                     False, "1", "PCID", False, "-1",
                                                                                     "PID", False, "1", "SCID", False,
                                                                                     "-1", "SID", False, "0"]],
                                       variations, ["X Component:=", "__InitialTime", "Y Component:=", ycomponents])
        return plotname

    def create_ami_statistical_eye_plot(self, setupname, ami_name, variation_list_w_value, ami_plot_type="InitialEye", plotname=None):
        """Create an AMI statistical eye plot.

        Parameters
        ----------
        setupname : str
            Name of the setup.
        probe_id : str
            AMI Probe Name to use
        variation_list_w_value : list
            List of variations with relative values.
        plot_type : str, optional
            String containing the report type. Default is ``"Rectangular Plot"``. It can be ``"Data Table"``,
            ``"Rectangular Stacked Plot"``, or any other valid AEDT report types.
        ami_plot_type : str, optional
            String containing the report AMI type. Default is ``"InitialEye"``. It can be ``"EyeAfterSource"``,
            ``"EyeAfterChannel"`` or ``"EyeAfterProbe"``.
        plotname: str, optional
            The name of the plot.  Defaults to a unique name starting with ``"Plot"``.

        Returns
        -------
        str
           The name of the plot.
        """
        if not plotname:
            plotname = generate_unique_name("AMYAanalysis")
        variations = ["__UnitInterval:=", ["All"],"__Amplitude:="	, ["All"],]
        i = 0
        for a in variation_list_w_value:
            if (i % 2) == 0:
                if ":=" in a:
                    variations.append(a)
                else:
                    variations.append(a + ":=")
            else:
                if isinstance(a, list):
                    variations.append(a)
                else:
                    variations.append([a])
            i += 1
        ycomponents = []
        if ami_plot_type == "InitialEye" or ami_plot_type == "EyeAfterSource":
            ibs_type = "tx"
        else:
            ibs_type = "rx"
        ycomponents.append("{}<{}.int_ami_{}>".format(ami_plot_type, ami_name, ibs_type))

        ami_id = "0"
        if ami_plot_type == "EyeAfterSource":
            ami_id = "1"
        elif ami_plot_type == "EyeAfterChannel":
            ami_id = "2"
        elif ami_plot_type == "EyeAfterProbe":
            ami_id = "3"
        self.oreportsetup.CreateReport(plotname, "Statistical Eye", "Statistical Eye Plot", setupname,
                             [
                                 "NAME:Context",
                                 "SimValueContext:=",
                                 [55819, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0, "NUMLEVELS", False, "1",
                                  "QTID", False, ami_id, "SCID", False, "-1", "SID", False, "0"]
                             ],
                             variations,
                             [
                                 "X Component:="		, "__UnitInterval",
                                 "Y Component:="		, "__Amplitude",
                                 "Eye Diagram Component:=", ycomponents
                             ])
        return plotname

    def create_statistical_eye_plot(self, setupname, probe_names, variation_list_w_value, ami_plot_type="InitialEye", plotname=None):
        """Create a statistical QuickEye, VerifEye, and/or Statistical Eye plot.

        Parameters
        ----------
        setupname: str
            Name of the setup
        probe_names: str or list
            Name of the probe to plot in the EYE diagram.
        variation_list_w_value : list
            List of variations with relative values.
        plotname: str, optional
            The name of the plot.

        Returns
        -------
        str
            The name of the plot.
        """
        if not plotname:
            plotname = generate_unique_name("AMIAanalysis")
        variations = ["__UnitInterval:=", ["All"],"__Amplitude:="	, ["All"],]
        i = 0
        for a in variation_list_w_value:
            if (i % 2) == 0:
                if ":=" in a:
                    variations.append(a)
                else:
                    variations.append(a + ":=")
            else:
                if isinstance(a, list):
                    variations.append(a)
                else:
                    variations.append([a])
            i += 1
        if isinstance(probe_names, list):
            ycomponents = probe_names
        else:
            ycomponents = [probe_names]

        self.oreportsetup.CreateReport(plotname, "Statistical Eye", "Statistical Eye Plot", setupname,
                             [
                                 "NAME:Context",
                                 "SimValueContext:=",
                                 [55819, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0, "NUMLEVELS", False, "1",
                                  "QTID", False, "1", "SCID", False, "-1", "SID", False, "0"]
                             ],
                             variations,
                             [
                                 "X Component:="		, "__UnitInterval",
                                 "Y Component:="		, "__Amplitude",
                                 "Eye Diagram Component:=", ycomponents
                             ])
        return plotname
