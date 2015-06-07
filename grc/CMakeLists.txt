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
install(FILES
    ofdm_tools_clipper.xml
    ofdm_tools_papr_sink.xml
    ofdm_tools_ofdm_radio_hier.xml
    ofdm_tools_payload_source.xml
    ofdm_tools_payload_sink.xml
    ofdm_tools_spectrum_sensor.xml
    ofdm_tools_cognitive_engine_mac.xml
    ofdm_tools_sync_radio_hier.xml
    ofdm_tools_ascii_plot.xml
    ofdm_tools_ais_decoder.xml
    ofdm_tools_fosphor_main.xml
    ofdm_tools_spectrum_logger.xml
    ofdm_tools_psd_logger.xml
    ofdm_tools_spectrum_sensor_v1.xml
    ofdm_tools_flanck_detector.xml
    ofdm_tools_ofdm_tx_rx_hier.xml
    ofdm_tools_spectrum_sensor_v2.xml
    ofdm_tools_message_pdu.xml
    ofdm_tools_coherence_detector.xml
    ofdm_tools_payload_source_pdu.xml
    ofdm_tools_payload_sink_pdu.xml DESTINATION share/gnuradio/grc/blocks
)
