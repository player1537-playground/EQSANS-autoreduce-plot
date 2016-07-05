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

import scipy.stats

TOF_TEMPLATE = '''
<button id="plotly-slice-decrement" type="button">[-]</button>
<input id="plotly-slice-range" type="range"></input>
<button id="plotly-slice-increment" type="button">[+]</button>
<script>
(function() {
var graphDivs = document.getElementsByClassName('plotly-graph-div');
var graphDiv = graphDivs[0];
var index = 0;

function changeSlice() {
  for (var i=0; i<graphDiv.data.length; ++i) {
    graphDiv.data[i].visible = false;
  }

  graphDiv.data[index].visible = true;

  Plotly.redraw(graphDiv);
}

var range = document.getElementById("plotly-slice-range");
range.style.marginTop = "20px";
range.style.width = "80%";
range.min = 0;
range.max = graphDiv.data.length - 1;
range.value = 0;
range.addEventListener('change', function(e) {
  index = +e.target.value;
  changeSlice();
});

var decrement = document.getElementById("plotly-slice-decrement");
decrement.addEventListener('click', function(e) {
  e.preventDefault();
  if (index > 0) {
    index--;
  }
  range.value = index;
  changeSlice();
});

var increment = document.getElementById("plotly-slice-increment");
increment.addEventListener('click', function(e) {
  e.preventDefault();
  if (index < graphDiv.data.length - 2) {
    index++;
  }
  range.value = index;
  changeSlice();
});


})();
</script>
'''

def restructure_histogram_data(det_lookup, data, bins=None):
    Y = []
    X = []
    Z = []
    for index, val in enumerate(data):
        (i, j, _) = det_lookup[index]
        X.append(j)
        Y.append(i)
        Z.append(val)
    Y = np.array(Y)
    X = np.array(X)
    Z = np.array(Z)

    det_width = len(np.unique(X))
    det_height = len(np.unique(Y))

    if bins is None:
        bins = [det_width // 2, det_height // 2]

    Zp, xedges, yedges, _ = scipy.stats.binned_statistic_2d(
        X, Y, Z,
        bins=bins,
        statistic='mean',
    )

    Xp = xedges[1:] - (xedges[1] - xedges[0]) / 2
    Yp = yedges[1:] - (yedges[1] - yedges[0]) / 2

    return Zp

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
    det_lookup = {
        component[i][0][j].getID(): component[i][0][j].getPos()
        for i in xrange(component.nelements())
        for j in xrange(component[i][0].nelements())
    }

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
            restructure_histogram_data(det_lookup, rebinned_y[:, i])
            for i in range(num_bins)
        ]

    if plot_type == 'integrated' or plot_type == 'both':
        # Integrate along the time dimension to consolidate the data
        integration_workspace = mantid.simpleapi.Integration(workspace)

        # Get Y data
        integrated_y = integration_workspace.extractY()
        maximum = max(maximum, np.log(np.max(integrated_y)))

        # Restructure Y data
        integrated = restructure_histogram_data(det_lookup, integrated_y)

    rebinned_traces = []
    if plot_type == 'tof' or plot_type == 'both':
        for i, rebinned in enumerate(all_rebinned):
            # Mask out any values that will make taking the log difficult
            rebinned_z = rebinned
            rebinned_z = np.ma.masked_invalid(rebinned_z)
            mask = (0 < rebinned_z) & (rebinned_z < np.e)
            rebinned_z = np.ma.masked_where(mask, rebinned_z)
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

    import json
    import gzip
    with gzip.open('rebinned.json.gz', 'w') as f:
        json.dump([x.z.tolist() for x in rebinned_traces], f)

    integrated_traces = []
    if plot_type == 'integrated' or plot_type == 'both':
        # Mask out any values that will make taking the log difficult
        integrated_z = integrated
        integrated_z = np.ma.masked_invalid(integrated_z)
        mask = (0 < integrated_z) & (integrated_z < np.e)
        integrated_z = np.ma.masked_where(mask, integrated_z)
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
