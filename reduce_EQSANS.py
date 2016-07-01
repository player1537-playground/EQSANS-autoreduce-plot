#!/usr/bin/env python
"""Create a reduced image of the detector readings from a Mantid workspace.

This reduces the detector readings for each pixel by integrating in the time
dimension.

"""
from __future__ import print_function
from __future__ import division

import string

import mantid.simpleapi

import plotly
import plotly.offline
import plotly.graph_objs

import numpy as np

TOF_TEMPLATE = '''
<input id="plotly-slice-range" type="range"></input>
<script>
var graphDivs = document.getElementsByClassName('plotly-graph-div');
var graphDiv = graphDivs[0];

function changeSlice(index) {
  for (var i=0; i<graphDiv.data.length; ++i) {
    graphDiv.data[i].visible = false;
  }

  graphDiv.data[index].visible = true;

  Plotly.redraw(graphDiv);
}

var range = document.getElementById("plotly-slice-range");
range.style.marginTop = "20px";
range.min = 0;
range.max = graphDiv.data.length - 1;
range.addEventListener('change', function(e) {
  console.log(e);
  changeSlice(+e.target.value);
});
</script>
'''

def restructure_histogram_data(data, det_width, det_height, subdivs=8):
    # Not entirely sure why this needs to be here. As it is now, it rearranges
    # some of the columns so that they match the 2D space of the detector
    # correctly.
    #
    # For example, when subdivs = 8 and det_width = 192, then we take the
    # detector and split it into 8 groups along the x axis, meaning that we end
    # up with 192/8=24 columns in every group. Then we want to take the first
    # group, and the 8//2+1=5th group and arrange them next to each other, and
    # so on for the rest of the columns (2 and 6, 3 and 7, 4 and 8).
    #
    # You can experiment with different subdivs, but this seems to be working
    # correctly, although it's definitely a hack.
    indices = [x+y*subdivs//2 for x in range(subdivs // 2) for y in range(2)]

    # Apply the subdivisions as well as reshape the 1 dimensions Y values that
    # we get from Mantid into a 2D matrix of shape (height, width)
    data = data.reshape(det_width // subdivs, subdivs, det_height)
    data = data.T[:, indices, :].T
    data = data.reshape(det_width, det_height)
    data = data.T

    return data

def main(filename, outdir, output_type, include_plotly_js, plot_type, bin_width,
         num_bins):
    # Load the workspace
    workspace = mantid.simpleapi.Load(filename)
    run_number = workspace.getRunNumber()

    # Get the detector width and height from the workspace
    instrument = workspace.getInstrument()
    component = instrument[instrument.nelements() - 1]
    det_width = component.nelements()
    det_height = component[0][0].nelements()

    # Get the number of time units from workspace and calculate bin width
    blocksize = workspace.blocksize()
    if not bin_width:
        bin_width = blocksize // num_bins
    else:
        num_bins = blocksize // bin_width

    maximum = 0

    if plot_type == 'tof' or plot_type == 'both':
        # Rebin data
        rebinned_workspace = mantid.simpleapi.Rebin(
            workspace,
            Params='{},{},{}'.format(0, bin_width, bin_width * num_bins),
            FullBinsOnly=True,
        )

        rebinned_y = rebinned_workspace.extractY()
        maximum = max(maximum, np.log(np.max(rebinned_y)))

        all_rebinned = [
            restructure_histogram_data(rebinned_y[:, i], det_width, det_height)
            for i in range(num_bins)
        ]

    if plot_type == 'integrated' or plot_type == 'both':
        # Integrate along the time dimension to consolidate the data
        integration_workspace = mantid.simpleapi.Integration(workspace)

        # Get Y data
        integrated_y = integration_workspace.extractY()
        maximum = max(maximum, np.log(np.max(integrated_y)))

        # Restructure Y data
        integrated = restructure_histogram_data(integrated_y, det_width, det_height)

    rebinned_traces = []
    if plot_type == 'tof' or plot_type == 'both':
        for i, rebinned in enumerate(all_rebinned):
            # Mask out any values that will make taking the log difficult
            mask = (0 < rebinned) & (rebinned < np.e)
            rebinned_z = np.ma.masked_where(mask, rebinned)
            rebinned_z = np.ma.log(rebinned_z)

            # Actually plot the data
            rebinned_trace = plotly.graph_objs.Heatmap(
                z=rebinned_z,
                zmax=maximum,
                visible=True if (i == 0) else 'legendonly',
                showlegend=True,
                name='Rebinned {}'.format(i),
            )

            rebinned_traces.append(rebinned_trace)

    integrated_traces = []
    if plot_type == 'integrated' or plot_type == 'both':
        # Mask out any values that will make taking the log difficult
        mask = (0 < integrated) & (integrated < np.e)
        integrated_z = np.ma.masked_where(mask, integrated)
        integrated_z = np.ma.log(integrated_z)

        integrated_trace = plotly.graph_objs.Heatmap(
            z=Z,
            zmax=maximum,
        )

        integrated_traces.append(integrated_trace)

    layout = plotly.graph_objs.Layout(
        xaxis=dict(title='Tube'),
        yaxis=dict(title='Pixel'),
        showlegend=True,
    )

    print(len(integrated_traces + rebinned_traces))

    fig = plotly.graph_objs.Figure(
        data=integrated_traces + rebinned_traces,
        layout=layout,
    )

    # Save image to the disk
    output_filename = "EQSANS_{}_autoreduced.html".format(run_number)
    output_path = os.path.join(outdir, output_filename)

    if output_type == 'div':
        div = plotly.offline.plot(fig, output_type='div',
                                  include_plotlyjs=include_plotly_js)
        with open(output_path, 'w') as f:
            f.write(div)

    else: # output_type == 'file':
        plotly.offline.plot(fig, filename=output_path,
                            include_plotlyjs=include_plotly_js)



    if plot_type == 'tof' or plot_type == 'integrated':
        with open(output_path, 'a') as f:
            f.write(TOF_TEMPLATE)

if __name__ == "__main__":
    import argparse
    import os

    def path_exists(path):
        """Ensures that the paths provided by the user exist"""
        if not os.path.exists(path):
            raise argparse.ArgumentTypeError("{} does not exist".format(path))
        return path

    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=path_exists)
    parser.add_argument('outdir', type=path_exists)
    parser.add_argument('--output-type', choices=('div', 'file'), default='div')
    include_plotly_js = parser.add_mutually_exclusive_group(required=False)
    include_plotly_js.add_argument('--include-plotly-js',
                                   dest='include_plotly_js',
                                   action='store_true')
    include_plotly_js.add_argument('--no-include-plotly-js',
                                   dest='include_plotly_js',
                                   action='store_false')
    parser.set_defaults(include_plotly_js=True)
    parser.add_argument('--plot-type', choices=('integrated', 'tof', 'both'),
                        default='integrated')
    parser.add_argument('--bin-width', type=int, default=None)
    parser.add_argument('--num-bins', type=int, default=1)
    args = parser.parse_args()

    main(**vars(args))
