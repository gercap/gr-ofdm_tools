/* -*- c++ -*- */

#define OFDM_TOOLS_API

%include "gnuradio.i"			// the common stuff

//load generated python docstrings
%include "ofdm_tools_swig_doc.i"

%{
#include "ofdm_tools/clipper.h"
%}


%include "ofdm_tools/clipper.h"
GR_SWIG_BLOCK_MAGIC2(ofdm_tools, clipper);
