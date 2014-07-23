/* -*- c++ -*- */
/* 
 * Copyright 2014 <+YOU OR YOUR COMPANY+>.
 * 
 * This is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 3, or (at your option)
 * any later version.
 * 
 * This software is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this software; see the file COPYING.  If not, write to
 * the Free Software Foundation, Inc., 51 Franklin Street,
 * Boston, MA 02110-1301, USA.
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <gnuradio/io_signature.h>
#include "clipper_cc_impl.h"

namespace gr {
  namespace ofdm_tools {

	clipper_cc::sptr
	clipper_cc::make(double clip_fact)
	{
		return gnuradio::get_initial_sptr
			(new clipper_cc_impl(clip_fact));
	}

	/*
		* The private constructor
	*/
	clipper_cc_impl::clipper_cc_impl(double clip_fact)
		: gr::sync_block("clipper_cc",
			gr::io_signature::make(1, 1, sizeof(gr_complex)),
			gr::io_signature::make(1, 1, sizeof(gr_complex))),
	d_clip_fact(clip_fact) //get
	{
		set_clip_fact(clip_fact); //set
	}

	/*
		* Our virtual destructor.
	*/
	clipper_cc_impl::~clipper_cc_impl()
	{
	}

	int
	clipper_cc_impl::work(int noutput_items, gr_vector_const_void_star &input_items, gr_vector_void_star &output_items)
	{
		const gr_complex *in = (const gr_complex *) input_items[0];
		gr_complex *out = (gr_complex *) output_items[0];

		for(int i = 0; i < noutput_items; i++) {
		out[i] = in[i];

			if (in[i].real() > d_clip_fact) {
			out[i].real() = d_clip_fact;
			}
			if (in[i].real() < -d_clip_fact) {
			out[i].real() = -d_clip_fact;
			}
			if (in[i].imag() > d_clip_fact) {
			out[i].imag() = d_clip_fact;
			}
			if (in[i].imag() < -d_clip_fact) {
			out[i].imag() = -d_clip_fact;
			}
		}
	return noutput_items;
	}

	} /* namespace ofdm_tools */
} /* namespace gr */
