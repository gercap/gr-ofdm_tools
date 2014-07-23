ofdm_tools
==========

I named this module ofdm_tools, but the obejective is to build a 
VHF cognitive communication system for maritme applications

Basic project description:
- sensing framework detects PU activity
- cognitive engine decides spectrum usage and sets up transceivers
- master station synchronizes slaves stations with sensing extracted data
- congnitive engine keeps itself aware of the sorounding environment and periodically syncs slave stations

The firts part includes a reconfigurable OFDM transceiver (based on GNU Radio's ofdm_tx and ofdm_rx) and the basic sink / source blocks that interact w/ a TUN/TAP interface. This tranceiver has also input and output port to connect to USRP's or other blocks that may emulate hardware sinks.

The cognitive processing block that handles PDU's exchange w/ TUN/TAP interface is written in Python - not available yet
This cognitive engine also handles the sensing information that comes from the sensing framework also developed in Python- not available yet
In order to keep all network nodes synchronized, the cognitive engine comprises also a synchronization transceiver
