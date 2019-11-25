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

        def connectedInstruments(self):
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

