try:
    import pytest
except ImportError:
    import _unittest_ironpython.conf_unittest as pytest

# Setup paths for module imports
import gc
import math

# Import required modules
from _unittest.conftest import local_path, scratch_path
from pyaedt.hfss import Hfss
from pyaedt.application.Variables import Variable
from pyaedt.generic.filesystem import Scratch
from pyaedt.generic.general_methods import isclose
class TestClass:

    def setup_class(self):

        with Scratch(scratch_path) as self.local_scratch:
            self.aedtapp = Hfss()
            self._close_on_completion = True

    def teardown_class(self):

        if self._close_on_completion:
            assert self.aedtapp.close_project()
            self.local_scratch.remove()
            gc.collect()

    def test_01_set_globals(self):
        var = self.aedtapp.variable_manager
        self.aedtapp['$Test_Global1'] = "5rad"
        self.aedtapp['$Test_Global2'] = -1.0
        self.aedtapp['$Test_Global3'] = "0"
        self.aedtapp['$Test_Global4'] = "$Test_Global2*$Test_Global1"
        independent = self.aedtapp._variable_manager.independent_variable_names
        dependent = self.aedtapp._variable_manager.dependent_variable_names
        val = var['$Test_Global4']
        assert val.numeric_value == -5.0
        assert '$Test_Global1' in independent
        assert '$Test_Global2' in independent
        assert '$Test_Global3' in independent
        assert '$Test_Global4' in dependent
        pass

    def test_01_set_var_simple(self):
        var = self.aedtapp.variable_manager
        self.aedtapp['Var1'] = '1rpm'
        var_1 = self.aedtapp['Var1']
        var_2 = var['Var1'].string_value
        assert var_1 == var_2
        assert var['Var1'].numeric_value == 1.0
        pass

    def test_02_test_formula(self):
        self.aedtapp["Var1"] = 3
        self.aedtapp["Var2"] = "12deg"
        self.aedtapp["Var3"] = "Var1 * Var2"
        self.aedtapp["$PrjVar1"] = "2*pi"
        self.aedtapp["$PrjVar2"] = 45
        self.aedtapp["$PrjVar3"] = "sqrt(34 * $PrjVar2/$PrjVar1 )"

        v = self.aedtapp.variable_manager
        for var_name in v.variable_names:
            print("{} = {}".format(var_name, self.aedtapp[var_name]))
        pass

        c2pi = math.pi * 2.0
        assert v["$PrjVar1"].numeric_value == c2pi
        assert v["$PrjVar3"].numeric_value == math.sqrt(34 * 45.0/ c2pi )
        assert v["Var3"].numeric_value == 3.0 * 12.0 * math.pi / 180
        pass

    def test_03_test_evaluated_value(self):

        self.aedtapp["p1"] = "10mm"
        self.aedtapp["p2"] = "20mm"
        self.aedtapp["p3"] = "p1 * p2"
        v = self.aedtapp.variable_manager

        eval_p3_nom = v._parent.get_evaluated_value("p3")
        eval_p3_var = v._parent.get_evaluated_value("p3", variation="p1=100mm p2=20mm" )
        assert eval_p3_nom == 0.0002
        assert eval_p3_var == 0.002

    def test_04_set_variable(self):

        assert self.aedtapp.variable_manager.set_variable("p1", expression="10mm")
        assert self.aedtapp["p1"] == "10.0mm"
        assert self.aedtapp.variable_manager.set_variable("p1", expression="20mm", overwrite=False)
        assert self.aedtapp["p1"] == "10.0mm"
        assert self.aedtapp.variable_manager.set_variable("p1", expression="30mm")
        assert self.aedtapp["p1"] == "30.0mm"
        assert self.aedtapp.variable_manager.set_variable(variable_name="p2", expression="10mm", readonly=True, hidden=True,
                                                          description="This is a description of this variable")
        assert self.aedtapp.variable_manager.set_variable("$p1", expression="10mm")

    def test_05_variable_class(self):

        v = Variable("4mm")
        num_value = v.numeric_value
        assert num_value == 4.0

        v = v.rescale_to("meter")
        test = v.string_value
        assert v.numeric_value == 0.004

        v = Variable("100cel")
        v.rescale_to("fah")
        assert v.numeric_value == 212.0
        pass

    def test_06_multiplication(self):

        v1 = Variable("10mm")
        v2 = Variable(3)
        v3 = Variable("3mA")
        v4 = Variable("40V")
        v5 = Variable("100NewtonMeter")
        v6 = Variable("1000rpm")

        result_1 = v1 * v2
        result_2 = v2 * v3
        result_3 = v3 * v4
        result_4 = v4 * v3
        result_5 = v4 * 24.0 * v3
        result_6 = v5 * v6
        result_7 = v6 * v5
        result_8 = (v5 * v6).rescale_to("kW")
        assert result_1.numeric_value == 30.0
        assert result_1.unit_system == "Length"

        assert result_2.numeric_value == 9.0
        assert result_2.units == "mA"
        assert result_2.unit_system == "Current"

        assert result_3.numeric_value == 0.12
        assert result_3.units == "W"
        assert result_3.unit_system == "Power"

        assert result_4.numeric_value == 0.12
        assert result_4.units == "W"
        assert result_4.unit_system == "Power"

        assert result_5.numeric_value == 2.88
        assert result_5.units == "W"
        assert result_5.unit_system == "Power"

        assert isclose(result_6.numeric_value, 10471.975511965977)
        assert result_6.units == "W"
        assert result_6.unit_system == "Power"

        assert isclose(result_7.numeric_value, 10471.975511965977)
        assert result_7.units == "W"
        assert result_7.unit_system == "Power"

        assert isclose(result_8.numeric_value, 10.471975511965977)
        assert result_8.units == "kW"
        assert result_8.unit_system == "Power"

    def test_07_addition(self):

        v1 = Variable("10mm")
        v2 = Variable(3)
        v3 = Variable("3mA")
        v4 = Variable("10A")

        try:
            v1 + v2
            assert False
        except AssertionError:
            pass

        try:
            v2 + v1
            assert False
        except AssertionError:
            pass
        result_1 = v2 + v2
        result_2 = v3 + v4
        result_3 = v3 + v3

        assert result_1.numeric_value == 6.0
        assert result_1.unit_system == "None"

        assert result_2.numeric_value == 10.003
        assert result_2.units == "A"
        assert result_2.unit_system == "Current"

        assert result_3.numeric_value == 6.0
        assert result_3.units == "mA"
        assert result_3.unit_system == "Current"

    def test_08_subtraction(self):

        v1 = Variable("10mm")
        v2 = Variable(3)
        v3 = Variable("3mA")
        v4 = Variable("10A")

        try:
            v1 - v2
            assert False
        except AssertionError:
            pass

        try:
            v2 - v1
            assert False
        except AssertionError:
            pass

        result_1 = v2 - v2
        result_2 = v3 - v4
        result_3 = v3 - v3

        assert result_1.numeric_value == 0.0
        assert result_1.unit_system == "None"

        assert result_2.numeric_value == -9.997
        assert result_2.units == "A"
        assert result_2.unit_system == "Current"

        assert result_3.numeric_value == 0.0
        assert result_3.units == "mA"
        assert result_3.unit_system == "Current"

    def test_09_specify_units(self):

        # Scaling of the unit system "Angle"
        angle = Variable("1rad")
        angle.rescale_to("deg")
        assert isclose(angle.numeric_value, 57.29577951308232)
        angle.rescale_to("degmin")
        assert isclose(angle.numeric_value, 57.29577951308232 * 60.0)
        angle.rescale_to("degsec")
        assert isclose(angle.numeric_value, 57.29577951308232 * 3600.0)

        # Convert 200Hz to Angular speed numerically
        omega = Variable(200 * math.pi*2, "rad_per_sec")
        assert omega.unit_system == 'AngularSpeed'
        assert isclose(omega.value, 1256.6370614359173)
        omega.rescale_to('rpm')
        assert isclose(omega.numeric_value, 12000.0)
        omega.rescale_to('rev_per_sec')
        assert isclose(omega.numeric_value, 200.0)

        # test speed times time equals diestance
        v = Variable("100m_per_sec")
        assert v.unit_system == "Speed"
        v.rescale_to('feet_per_sec')
        assert isclose(v.numeric_value, 328.08398950131)
        v.rescale_to('feet_per_min')
        assert isclose(v.numeric_value, 328.08398950131 * 60)
        v.rescale_to('miles_per_sec')
        assert isclose(v.numeric_value, 0.06213711723534)
        v.rescale_to('miles_per_minute')
        assert isclose(v.numeric_value, 3.72822703412)
        v.rescale_to('miles_per_hour')
        assert isclose(v.numeric_value, 223.69362204724)

        t = Variable("20s")
        distance = v * t
        assert distance.unit_system == "Length"
        assert distance.string_value == "2000.0meter"
        distance.rescale_to("in")
        assert isclose(distance.numeric_value, 2000 / 0.0254)

    def test_10_division(self):
        '''
            'Power_divide_Voltage': 'Current',
            'Power_divide_Current': 'Voltage',
            'Power_divide_AngularSpeed': 'Torque',
            'Power_divide_Torque': 'Angular_Speed',
            'Angle_divide_AngularSpeed': 'Time',
            'Angle_divide_Time': 'AngularSpeed',
            'Voltage_divide_Current': 'Resistance',
            'Voltage_divide_Resistance': 'Current',
            'Resistance_divide_AngularSpeed': 'Inductance',
            'Resistance_divide_Inductance': 'AngularSpeed',
            'None_divide_Freq': 'Time',
            'None_divide_Time': 'Freq',
            'Length_divide_Time': 'Speed',
            'Length_divide_Speed': 'Time'
        '''

        v1 = Variable("10W")
        v2 = Variable("40V")
        v3 = Variable("1s")
        v4 = Variable("3mA")
        v5 = Variable("100NewtonMeter")
        v6 = Variable("1000rpm")

        result_1 = v1 / v2
        assert result_1.numeric_value == 0.25
        assert result_1.units == "A"
        assert result_1.unit_system == "Current"

        result_2 = v2 / result_1
        assert result_2.numeric_value == 160.0
        assert result_2.units == "ohm"
        assert result_2.unit_system == "Resistance"

        result_3 = 3 / v3
        assert result_3.numeric_value == 3.0
        assert result_3.units == "Hz"
        assert result_3.unit_system == "Freq"

        result_4 = v3 / 3
        assert result_4.numeric_value == 0.3333333333333333333333
        assert result_4.units == "s"
        assert result_4.unit_system == "Time"

        result_5 = v4 / v5
        assert result_5.numeric_value == 0.00003
        assert result_5.units == ""
        assert result_5.unit_system == "None"

        result_6 = v1 / v5 + v6
        assert isclose(result_6.numeric_value, 104.81975511965)
        assert result_6.units == "rad_per_sec"
        assert result_6.unit_system == "AngularSpeed"

    def test_11_delete_variable(self):
        assert self.aedtapp.variable_manager.delete_variable("Var1")
