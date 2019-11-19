# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from collections import OrderedDict

import logging
import numpy

from modules.quantity import Q
from .ExternalParameterBase import ExternalParameterBase
from ProjectConfig.Project import getProject
from uiModules.ImportErrorPopup import importErrorPopup
from .qtHelper import qtHelper
import time

project = getProject()
visaEnabled = project.isEnabled('hardware', 'VISA')
from PyQt5 import QtCore

if visaEnabled:
    try:
        import visa
    except ImportError:  # popup on failed import of enabled visa
        importErrorPopup('VISA')

SRS_DS345_Enabled = project.isEnabled('hardware', 'QITI SRS DS345 Function Generator')

if SRS_DS345_Enabled:
    from QITI_communicate_instruments.srs.ds345 import DS345


    class SRS_DS345_FunctionGenerator(ExternalParameterBase):
        '''
        Communicate with the SRS DS345 function generator.
        
        instrument(str) -> name of the instrument should match with the name given on the initial project config
        
        '''
        className = 'QITI SRS DS345 Function Generator'''
        _outputChannels = OrderedDict([('Frequency', 'kHz'),
                                       ('Amplitude(Vpp)', 'V'),
                                       ('Offset', 'V'),
                                       ('Function', '')])
        # _inputChannels = OrderedDict([('Frequency','kHz'),
        # ('Amplitude(Vpp)','V'),
        # ('Offset','V'),
        # ('Function','')])
        _outputLookup = {'Frequency': ('frequency', 'Hz'),
                         'Amplitude(Vpp)': ('amplitude', 'V'),
                         'Offset': ('offset', 'V'),
                         'Function': ('function', '')}

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI SRS DS345 Function Generator')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('Prologix IP')
            gpib_addr = instrument.get('GPIB Addr')
            self.DS345 = DS345(ip_addr, gpib_addr)
            logger.info("Trying to connect to the DS345 Function generator {0},{1}".format(ip_addr, gpib_addr))
            self.DS345.connect()
            self.initializeChannelsToExternals()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

        def setValue(self, channel, v):
            func_name, unit = self._outputLookup[channel]
            setattr(self.DS345, func_name, v.m_as(unit))
            return v

        def getValue(self, channel):
            func_name, unit = self._outputLookup[channel]
            v = getattr(self.DS345, func_name)
            return Q(v, unit)

        def getExternalValue(self, channel):
            return self.getValue(channel)

        def connectedInstruments():
            project = getProject()
            instrument_list = project.hardware.get('QITI SRS DS345 Function Generator').keys()
            return instrument_list

laserfreqPID_Enabled = project.isEnabled('hardware', 'QITI Laser Frequency PID Lock')

if laserfreqPID_Enabled:
    try:
        from QITI_WavemeterLock.PID_client.PID_client import ConfigREQClient
    except ImportError:
        importErrorPopup('Laser Frequency PID client')


    class LaserFreqPID(ExternalParameterBase):
        """
        Adjust the freq_setpoint and the lock status of the laser frequency PID lock
        """
        className = 'QITI Laser Frequency PID Lock'
        _outputChannels = OrderedDict([("FrequencySetpoint", "THz"), ("EnableLock", "")])
        _inputChannels = OrderedDict([("FrequencySetpoint", "THz"), ("EnableLock", "")])
        _outputLookup = {
            'FrequencySetpoint': ("freq_setpoint", "THz", lambda x: eval(x)[0], lambda x: str([x])),
            "EnableLock": ("enable_lock", "", lambda v: float(v == 'True'), lambda v: str(bool(v)))
        }

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            server_list = project.hardware.get('QITI Laser Frequency PID Lock').items()
            server_name, server = list(server_list)[0]
            server_address, server_port = server.get('PIDServerAddress').split(":")
            self.instrument = instrument
            self.client_config = {
                'server_settings':
                    {
                        'config_server_ip': server_address,
                        'config_request_port': server_port
                    },
                instrument:
                    {'freq_setpoint': None,
                     'enable_lock': None
                     }
            }
            self.ConfigREQClient = ConfigREQClient(self.client_config)
            logger.info("Trying to connect to the PID server {0}".format(server))
            self.ConfigREQClient.connect()
            self.initializeChannelsToExternals()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

            # self.initOutput()

        def setValue(self, channel, v):
            config_name, unit, get_func, set_func = self._outputLookup[channel]
            self.client_config[self.instrument][config_name] = set_func(v.m_as(unit))
            self.ConfigREQClient.update_config(self.client_config)
            self.ConfigREQClient.set_config()
            self.newData.emit(self.name + "_" + channel, (time.time(), self.getValue(channel)))
            return v

        def getValue(self, channel):
            config_name, unit, get_func, set_func = self._outputLookup[channel]
            self.client_config = self.ConfigREQClient.get_config()
            return Q(get_func(self.client_config[self.instrument][config_name]), unit)

        def getExternalValue(self, channel):
            # config_name,unit,get_func,set_func = self._outputLookup[channel]
            # return Q( get_func(self.client_config[self.instrument][config_name]), unit )
            return self.getValue(channel)

DC_Controller_Enabled = project.isEnabled('hardware', 'QITI Four rod DC Controller')

if DC_Controller_Enabled:
    try:
        from QITI_DC_Voltage_Control.src.DC_voltage_control_python.dc_ctr_rpc_client import FourRodDCControllerClient
        from QITI_DC_Voltage_Control.src.DC_voltage_control_python.dc_ctr_enum import *
    except ImportError:
        importErrorPopup('DC Voltage Control')


    class DCVoltageControl(ExternalParameterBase):
        """
        Control the voltages on rods and needles for the four rod trap
        """
        className = "Four rod DC Voltage Control"
        _outputChannels = OrderedDict([
            ('Enable Remote Control', ''),
            ('Needle_1_Voltage', 'V'),
            ('Needle_2_Voltage', 'V'),
            ('Rod_1_Voltage', 'V'),
            ('Rod_2_Voltage', 'V'),
            ('Rod_3_Voltage', 'V'),
            ('Rod_4_Voltage', 'V')])

        _outputLookup = {
            'Needle_1_Voltage': CHANNEL_N1,
            'Needle_2_Voltage': CHANNEL_N2,
            'Rod_1_Voltage': CHANNEL_R1,
            'Rod_2_Voltage': CHANNEL_R2,
            'Rod_3_Voltage': CHANNEL_R3,
            'Rod_4_Voltage': CHANNEL_R4
        }

        def __init__(self, name, config, globalDict, instrument):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            project = getProject()
            instrument_list = project.hardware.get('QITI Four rod DC Controller')
            instrument = instrument_list[instrument]
            ip_addr = instrument.get('ipAddress')
            port = instrument.get('port')
            self.dc_client = FourRodDCControllerClient(address=ip_addr + ':' + port)
            
            # self.initializeChannelsToExternals()
            # self.initOutput()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData

        def setValue(self, channel, v):
            if channel == 'Enable Remote Control':
                v = v.m_as('')
                v = int(v)
                if v not in (0, 1, 255):
                    raise ValueError("Not an available mode!!!!!")
                self.dc_client.set_mode_all(v)
            else:
                v = v.m_as('V')
                v = float(v)
                v_channel = self._outputLookup[channel]
                print(v_channel, v)
                self.dc_client.set_volt(v_channel, v)

        def getExternalValue(self, channel=None):
            if channel == 'Enable Remote Control':
                mode = self.dc_client.get_mode(CHANNEL_N1)
                return Q(mode, '')
            else:
                v_channel = self._outputLookup[channel]
                voltage = self.dc_client.get_volt_adc(v_channel)
                return Q(voltage, 'V')

        def connectedInstruments(self):
            project = getProject()
            instrument_list = project.hardware.get('QITI Four rod DC Controller').keys()
            return instrument_list

if visaEnabled:
    class N6700BPowerSupply(ExternalParameterBase):
        """
        Adjust the current on the N6700B current supply
        """
        className = "N6700 Powersupply"
        _outputChannels = OrderedDict([("Curr1", "A"), ("Curr2", "A"), ("Curr3", "A"), ("Curr4", "A"), ("Volt1", "V"),
                                       ("Volt2", "V"), ("Volt3", "V"), ("Volt4", "V"), ("OutEnable1", ""),
                                       ("OutEnable2", ""), ("OutEnable3", ""), ("OutEnable4", "")])
        _outputLookup = {"Curr1": ("Curr", "Meas:Curr", 1, "A"), "Curr2": ("Curr", "Meas:Curr", 2, "A"),
                         "Curr3": ("Curr", "Meas:Curr", 3, "A"), "Curr4": ("Curr", "Meas:Curr", 4, "A"),
                         "Volt1": ("Volt", "Meas:Volt", 1, "V"), "Volt2": ("Volt", "Meas:Volt", 2, "V"),
                         "Volt3": ("Volt", "Meas:Volt", 3, "V"), "Volt4": ("Volt", "Meas:Volt", 4, "V"),
                         "OutEnable1": ("OUTP:STAT", "OUTP:STAT", 1, ""),
                         "OutEnable2": ("OUTP:STAT", "OUTP:STAT", 2, ""),
                         "OutEnable3": ("OUTP:STAT", "OUTP:STAT", 3, ""),
                         "OutEnable4": ("OUTP:STAT", "OUTP:STAT", 4, "")}
        _inputChannels = dict(
            {"Curr1": "A", "Curr2": "A", "Curr3": "A", "Curr4": "A", "Volt1": "V", "Volt2": "V", "Volt3": "V",
             "Volt4": "V"})

        def __init__(self, name, config, globalDict, instrument="QGABField"):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            logger.info("trying to open '{0}'".format(instrument))
            self.rm = visa.ResourceManager()
            self.instrument = self.rm.open_resource(instrument)
            logger.info("opened {0}".format(instrument))
            self.setDefaults()
            self.initializeChannelsToExternals()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData
            self.initOutput()

        def setValue(self, channel, v):
            function, _, index, unit = self._outputLookup[channel]
            command = "{0} {1},(@{2})".format(function, v.m_as(unit), index)
            self.instrument.write(command)  # set voltage
            return v

        def getValue(self, channel):
            function, _, index, unit = self._outputLookup[channel]
            command = "{0}? (@{1})".format(function, index)
            return Q(float(self.instrument.query(command)), unit)  # set voltage

        def getExternalValue(self, channel):
            _, function, index, unit = self._outputLookup[channel]
            command = "{0}? (@{1})".format(function, index)
            value = Q(float(self.instrument.query(command)), unit)
            return value

        def close(self):
            del self.instrument


    class AFG3102(ExternalParameterBase):
        """
        Adjust parameters on the AFG3102 tektronix arbitrary function generator
        """
        className = "AFG3102 Arbitrary Function Generator"
        _outputChannels = OrderedDict([("OutEnable1", ""),
                                       ("OutEnable2", ""),
                                       ("Freq1", "Hz"),
                                       ("Freq2", "Hz"),
                                       ("Amp1", "V"),
                                       ("Amp2", "V"),
                                       # ("SweepEnabled1", ""),
                                       # ("SweepEnabled2", ""),
                                       ("SweepStartFreq1", "Hz"),
                                       ("SweepStartFreq2", "Hz"),
                                       ("SweepStopFreq1", "Hz"),
                                       ("SweepStopFreq2", "Hz"),
                                       ("SweepTime1", "s"),
                                       ("SweepTime2", "s"),
                                       ("SweepReturnTime1", "s"),
                                       ("SweepReturnTime2", "s")]
                                      )

        _outputLookup = {"OutEnable1": ("OUTP1:STAT", 1, ""),
                         "OutEnable2": ("OUTP2:STAT", 2, ""),
                         "Freq1": ("SOUR1:FREQ:CENT", 1, "Hz"),
                         "Freq2": ("SOUR2:FREQ:CENT", 2, "Hz"),
                         "Amp1": ("SOUR1:VOLT:AMPL", 1, "V"),
                         "Amp2": ("SOUR2:VOLT:AMPL", 2, "V"),
                         # "SweepEnabled1": ("SOUR1:FREQ:MODE", 0, ""),
                         # "SweepEnabled2": ("SOUR2:FREQ:MODE", 0, ""),
                         "SweepStartFreq1": ("SOUR1:FREQ:STAR", 1, "Hz"),
                         "SweepStartFreq2": ("SOUR2:FREQ:STAR", 2, "Hz"),
                         "SweepStopFreq1": ("SOUR1:FREQ:STOP", 1, "Hz"),
                         "SweepStopFreq2": ("SOUR2:FREQ:STOP", 2, "Hz"),
                         "SweepTime1": ("SOUR1:SWE:TIME", 1, "s"),
                         "SweepTime2": ("SOUR2:SWE:TIME", 2, "s"),
                         "SweepReturnTime1": ("SOUR1:SWE:RTIM", 1, "s"),
                         "SweepReturnTime2": ("SOUR2:SWE:RTIM", 2, "s")}

        _inputChannels = {"OutEnable1": "",
                          "OutEnable2": "",
                          "Freq1": "Hz",
                          "Freq2": "Hz",
                          "Amp1": "V",
                          "Amp2": "V",
                          # "SweepEnabled1": "",
                          # "SweepEnabled2": "",
                          "SweepStartFreq1": "Hz",
                          "SweepStartFreq2": "Hz",
                          "SweepStopFreq1": "Hz",
                          "SweepStopFreq2": "Hz",
                          "SweepTime1": "s",
                          "SweepTime2": "s",
                          "SweepReturnTime1": "s",
                          "SweepReturnTime2": "s"}

        # _outputLookup = { "Curr1": ("Curr", 1, "A"), "Curr2": ("Curr", 2, "A"), "Curr3": ("Curr", 3, "A"), "Curr4": ("Curr", 4, "A"),
        # "Volt1": ("Volt", 1, "V"), "Volt2": ("Volt", 2, "V"), "Volt3": ("Volt", 3, "V"), "Volt4": ("Volt", 4, "V"),
        # "OutEnable1": ("OUTP:STAT", 1, ""), "OutEnable2": ("OUTP:STAT", 2, ""),
        # "OutEnable3": ("OUTP:STAT", 3, ""), "OutEnable4": ("OUTP:STAT", 4, "")}
        # _inputChannels = dict({"Curr1":"A", "Curr2":"A", "Curr3":"A", "Curr4":"A", "Volt1":"V", "Volt2":"V", "Volt3":"V", "Volt4":"V"})
        def __init__(self, name, config, globalDict, instrument="QGABField"):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            logger.info("trying to open '{0}'".format(instrument))
            self.rm = visa.ResourceManager()
            self.instrument = self.rm.open_resource(instrument)
            logger.info("opened {0}".format(instrument))
            self.setDefaults()
            self.initializeChannelsToExternals()
            self.qtHelper = qtHelper()
            self.newData = self.qtHelper.newData
            self.initOutput()

        def setValue(self, channel, v):
            function, index, unit = self._outputLookup[channel]
            command = "{0} {1}".format(function, v.m_as(unit))  # , index)
            self.instrument.write(command)  # set voltage
            return v

        def getValue(self, channel):
            function, index, unit = self._outputLookup[channel]
            command = "{0}?".format(function)  # , index)
            try:
                return Q(float(self.instrument.query(command)), unit)  # set voltage
            except:
                return self.instrument.query(command)

        def getExternalValue(self, channel):
            function, index, unit = self._outputLookup[channel]
            command = "{0}?".format(function)  # , index)
            value = Q(float(self.instrument.query(command)), unit)
            return value

        def close(self):
            del self.instrument


    class HP8672A(ExternalParameterBase):
        """
        Scan the laser frequency by scanning a synthesizer HP8672A. (The laser is locked to a sideband)
        setValue is frequency of synthesizer
        currentValue and currentExternalValue are current frequency of synthesizer

        This class programs the 8672A using the directions in the manual, p. 3-17: cp.literature.agilent.com/litweb/pdf/08672-90086.pdf
        """
        className = "HP8672A"
        _outputChannels = {'Freq': 'MHz', 'Power_dBm': ''}

        def __init__(self, name, config, globalDict, instrument="GPIB0::23::INSTR"):
            ExternalParameterBase.__init__(self, name, config, globalDict)
            self.setDefaults()
            initialAmplitudeString = self.createAmplitudeString()
            self.rm = visa.ResourceManager()
            self.synthesizer = self.rm.open_resource(instrument)
            self.synthesizer.write(initialAmplitudeString)
            self.initOutput()

        def setValue(self, channel, value):
            """Send the command string to the HP8672A to set the frequency to 'value'."""
            if channel == 'Freq':
                value = value.round('kHz')
                command = "P{0:0>8.0f}".format(value.m_as('kHz')) + 'Z0' + self.createAmplitudeString()
                # Example string: P03205000Z0K1L6O1 would set the oscillator to 3.205 GHz, -13 dBm
            elif channel == 'Power_dBm':
                command = self.createAmplitudeString(value)
            self.synthesizer.write(command)
            return value

        def createAmplitudeString(self, value=None):
            """Create the string for setting the HP8672A amplitude.
            The string is of the form K_L_O_, where _ is a number or symbol indicating an amplitude."""
            KDict = {0: '0', -10: '1', -20: '2', -30: '3', -40: '4', -50: '5', -60: '6', -70: '7', -80: '8', -90: '9',
                     -100: ':', -110: ';'}
            LDict = {3: '0', 2: '1', 1: '2', 0: '3', -1: '4', -2: '5', -3: '6', -4: '7', -5: '8', -6: '9', -7: ':',
                     -8: ';', -9: '<', -10: '='}
            amp = int(
                round(value)) if value else 0  # convert the amplitude to a number, and round it to the nearest integer
            amp = max(-120, min(amp, 13))  # clamp the amplitude to be between -120 and +13
            Opart = '1' if amp <= 3 else '3'  # Determine if the +10 dBm range option is necessary
            if Opart == '3':
                amp -= 10
            if amp >= 0:
                Kpart = KDict[0]
                Lpart = LDict[amp]
            else:
                Kpart = KDict[10 * (divmod(amp, 10)[0] + 1)]
                Lpart = LDict[divmod(amp, 10)[1] - 10]
            return 'K' + Kpart + 'L' + Lpart + 'O' + Opart

        def close(self):
            del self.synthesizer


    class MicrowaveSynthesizer(ExternalParameterBase):
        """
        Scan the microwave frequency of microwave synthesizer
        """
        className = "Microwave Synthesizer"
        _outputChannels = {'Freq': 'MHz', 'Power_dBm': ''}

        def __init__(self, name, config, globalDict, instrument="GPIB0::23::INSTR"):
            ExternalParameterBase.__init__(self, name, config, globalDict)
            self.rm = visa.ResourceManager()
            self.synthesizer = self.rm.open_resource(instrument)
            self.setDefaults()
            self.initializeChannelsToExternals()
            self.initOutput()

        def setValue(self, channel, v):
            if channel == 'Freq':
                command = ":FREQ:CW {0:.5f}KHZ".format(v.m_as('kHz'))
            elif channel == 'Power_dBm':
                command = ":POWER {0:.3f}".format(float(v))
            self.synthesizer.write(command)
            return v

        def getValue(self, channel):
            if channel == 'Frequency':
                answer = self.synthesizer.query(":FREQ:CW?")
                return Q(float(answer), "Hz")
            elif channel == 'Power':
                answer = self.synthesizer.query(":POWER?")
                return Q(float(answer), "")

        def close(self):
            del self.synthesizer


    class E4422Synthesizer(ExternalParameterBase):
        """
        Scan the microwave frequency of microwave synthesizer
        """
        className = "E4422 Synthesizer"
        _outputChannels = {'Freq': 'MHz', 'Power_dBm': ''}

        def __init__(self, name, config, globalDict, instrument="GPIB0::23::INSTR"):
            ExternalParameterBase.__init__(self, name, config, globalDict)
            self.rm = visa.ResourceManager()
            self.synthesizer = self.rm.open_resource(instrument)
            self.setDefaults()
            self.initializeChannelsToExternals()
            self.initOutput()

        def setValue(self, channel, v):
            if channel == 'Freq':
                command = ":FREQ:CW {0:.5f}KHZ".format(v.m_as('kHz'))
            elif channel == 'Power_dBm':
                command = ":POWER {0:.3f}".format(float(v))
            self.synthesizer.write(command)
            return v

        def getValue(self, channel):
            if channel == 'Freq':
                answer = self.synthesizer.query(":FREQ:CW?")
                return Q(float(answer), "Hz")
            elif channel == 'Power_dBm':
                answer = self.synthesizer.query(":POWER?")
                return Q(float(answer), "")

        def close(self):
            del self.synthesizer


    class AgilentPowerSupply(ExternalParameterBase):
        """
        Scan a laser by changing the voltage on a HP power supply. The frequency is controlled via a VCO.
        setValue is voltage of vco
        currentValue and currentExternalValue are current applied voltage
        """
        className = "Agilent Powersupply"
        _outputChannels = {None: 'V'}

        def __init__(self, name, config, globalDict, instrument="power_supply_next_to_397_box"):
            ExternalParameterBase.__init__(self, name, config, globalDict)
            self.rm = visa.ResourceManager()
            self.powersupply = self.rm.open_resource(instrument)
            self.setDefaults()
            self.initializeChannelsToExternals()
            self.initOutput()

        def setDefaults(self):
            ExternalParameterBase.setDefaults(self)
            self.settings.__dict__.setdefault('AOMFreq', Q(1, 'MHz'))

        def setValue(self, channel, value):
            """
            Move one steps towards the target, return current value
            """
            self.powersupply.write("volt {0}".format(value.m_as('V')))
            return value

        def paramDef(self):
            superior = ExternalParameterBase.paramDef(self)
            superior.append({'name': 'AOMFreq', 'type': 'magnitude', 'value': self.settings.AOMFreq})
            return superior

        def close(self):
            del self.powersupply


    class HP6632B(ExternalParameterBase):
        """
        Set the HP6632B power supply
        """
        className = "HP6632B Power Supply"
        _outputChannels = {"Curr": "A", "Volt": "V", "OnOff": ""}

        def __init__(self, name, config, globalDict, instrument="GPIB0::8::INSTR"):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            logger.info("trying to open '{0}'".format(instrument))
            self.rm = visa.ResourceManager()
            self.instrument = self.rm.open_resource(instrument)
            logger.info("opened {0}".format(instrument))
            self.setDefaults()
            self.initializeChannelsToExternals()
            self.initOutput()

        def setValue(self, channel, v):
            if channel == "OnOff":
                command = "OUTP ON" if v > 0 else "OUTP OFF"
            elif channel == "Curr":
                command = "Curr {0}".format(v.m_as('A'))
            elif channel == "Volt":
                command = "Volt {0}".format(v.m_as('V'))
            self.instrument.write(command)
            return v

        def getValue(self, channel):
            if channel == "OnOff":
                command, unit = "OUTP?", ""
            elif channel == "Curr":
                command, unit = "MEAS:Curr?", "A"
            elif channel == "Volt":
                command, unit = "Meas:Volt?", "V"
            value = Q(float(self.instrument.query(command)), unit)
            return value

        def close(self):
            del self.instrument


    class PTS3500(ExternalParameterBase):
        """
        Set the PTS3500 Frequency Source
        """
        className = "PTS3500 Frequency "
        _outputChannels = {"Freq": "GHz"}
        _outputLookup = {"Freq": ("F", "Hz", "\\nA1\\n")}

        def __init__(self, name, config, globalDict, instrument="GPIB0::16::INSTR"):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            logger.info("trying to open '{0}'".format(instrument))
            self.rm = visa.ResourceManager()
            self.instrument = self.rm.open_resource(instrument)
            self.setValue('Freq', self.settings.channelSettings[
                'Freq'].value)  # deals with the fact that PTS resets to zero when open_resource is called
            logger.info("opened {0}".format(instrument))
            self.setDefaults()
            self.initializeChannelsToExternals()
            self.initOutput()

        def setValue(self, channel, v):
            function, unit, suffix = self._outputLookup[channel]
            command = "{0}{1}{2}".format(function, int(v.m_as(unit)), suffix)
            self.instrument.write(command)
            return v

        def close(self):
            del self.instrument


    class DS345(ExternalParameterBase):
        """
        Set the DS345 SRS Function Generator
        """
        className = "DS345 SRS Function Generator "
        _outputChannels = {"Freq": "MHz", "Ampl": "dB"}
        _outputLookup = {"Freq": ("FREQ", "Hz"),
                         "Ampl": ("AMPL", "dB")}

        def __init__(self, name, config, globalDict, instrument="GPIB0::19::INSTR"):
            logger = logging.getLogger(__name__)
            ExternalParameterBase.__init__(self, name, config, globalDict)
            logger.info("trying to open '{0}'".format(instrument))
            self.rm = visa.ResourceManager()
            self.instrument = self.rm.open_resource(instrument)
            logger.info("opened {0}".format(instrument))
            self.setDefaults()
            self.initializeChannelsToExternals()
            self.initOutput()

        def setValue(self, channel, v):
            function, unit = self._outputLookup[channel]
            if channel == "Ampl":
                command = "{0}{1}DB".format(function, v.m_as(unit))
            else:
                command = "{0} {1}".format(function, v.m_as(unit))
            self.instrument.write(command)
            return v

        def close(self):
            del self.instrument


class DummyParameter(ExternalParameterBase):
    """
    DummyParameter, used to debug this part of the software.
    """
    className = "Dummy"
    _outputChannels = {'O1': "Hz", 'O7': "Hz"}

    def __init__(self, name, settings, globalDict, instrument=''):
        logger = logging.getLogger(__name__)
        ExternalParameterBase.__init__(self, name, settings, globalDict)
        logger.info("Opening DummyInstrument {0}".format(instrument))
        self.initializeChannelsToExternals()
        self.initOutput()

    def setValue(self, channel, value):
        logger = logging.getLogger(__name__)
        logger.info("Dummy output channel {0} set to: {1}".format(channel, value))
        return value


class DummySingleParameter(ExternalParameterBase):
    """
    DummyParameter, used to debug this part of the software.
    """
    className = "DummySingle"
    _outputChannels = {None: "Hz"}

    def __init__(self, name, settings, globalDict, instrument=''):
        logger = logging.getLogger(__name__)
        ExternalParameterBase.__init__(self, name, settings, globalDict)
        logger.info("Opening DummyInstrument {0}".format(instrument))
        self.initializeChannelsToExternals()
        self.initOutput()

    def setValue(self, channel, value):
        logger = logging.getLogger(__name__)
        logger.info("Dummy output channel {0} set to: {1}".format(channel, value))
        return value

    @classmethod
    def connectedInstruments(cls):
        return ['Anything will do']
