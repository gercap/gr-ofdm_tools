# Copyright 2011 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.

########################################################################
# Include python install macros
########################################################################
include(GrPython)
if(NOT PYTHONINTERP_FOUND)
    return()
endif()

########################################################################
# Install python sources
########################################################################
GR_PYTHON_INSTALL(
    FILES
    __init__.py
    papr_sink.py
    ofdm_radio_hier.py
    payload_source.py
    payload_sink.py
    spectrum_sensor.py
    ofdm_cr_tools.py
    cognitive_engine_mac.py
    sync_radio_hier.py
    ascii_plot.py
    ais_decoder.py
    fosphor_main.py
    spectrum_logger.py
    psd_logger.py
    spectrum_sensor_v1.py
    flanck_detector.py
    ofdm_tx_rx_hier.py
    ofdm_txrx_modules.py
    spectrum_sensor_v2.py
    message_pdu.py
    coherence_detector.py
    payload_source_pdu.py
    payload_sink_pdu.py
    chat_blocks.py DESTINATION ${GR_PYTHON_DIR}/ofdm_tools
)

########################################################################
# Handle the unit tests
########################################################################
include(GrTest)

set(GR_TEST_TARGET_DEPS gnuradio-ofdm_tools)
set(GR_TEST_PYTHON_DIRS ${CMAKE_BINARY_DIR}/swig)
