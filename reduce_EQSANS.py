#!/usr/bin/env python
"""Create a reduced image of the detector readings from a Mantid workspace.

This reduces the detector readings for each pixel by integrating in the time
dimension.

"""
from __future__ import print_function
from __future__ import division

import mantid.simpleapi

import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt

import numpy as np

def main(filename, outdir):
    # Load the workspace
    workspace = mantid.simpleapi.Load(filename)
    run_number = workspace.getRunNumber()

    # Get the detector width and height from the workspace
    instrument = workspace.getInstrument()
    component = instrument[instrument.nelements() - 1]
    det_width = component.nelements()
    det_height = component[0][0].nelements()

    # Integrate along the time dimension to consolidate the data
    integration_workspace = mantid.simpleapi.Integration(workspace)

    # Not entirely sure why this needs to be here. As it is now, it rearranges
    # some of the columns so that they match the 2D space of the detector
    # correctly.
    #
    # For example, when subdivs = 8 and det_width = 192, then we take the
    # detector and split it into 8 groups along the x axis, meaning that we end
    # up with 192/8=24 columns in every group. Then we want to take the first
    # group, and the 8//2+1=5th group and arrange them next to each other.
    #
    # You can experiment with different subdivs, but this seems to be working
    # correctly, although it's definitely a hack.
    subdivs = 8
    indices = [x+y*subdivs//2 for x in range(subdivs // 2) for y in range(2)]

    # Apply the subdivisions as well as reshape the 1 dimensions Y values that
    # we get from Mantid into a 2D matrix of shape (height, width)
    integrated = integration_workspace.extractY()
    integrated = integrated.reshape(det_width // subdivs, subdivs, det_height)
    integrated = integrated.T[:, indices, :].T
    integrated = integrated.reshape(det_width, det_height)
    integrated = integrated.T

    # Mask out any values that will make taking the log difficult
    Z = np.ma.masked_where((0 < integrated) & (integrated < np.e), integrated)
    Z = np.ma.log(Z)

    # Actually plot the data
    plt.pcolormesh(Z)
    plt.colorbar()
    plt.ylim([0, det_height])
    plt.xlim([0, det_width])
    plt.xlabel('Tube')
    plt.ylabel('Pixel')

    # Save image to the disk
    output_filename = "EQSANS_{}_autoreduced.png".format(run_number)
    output_path = os.path.join(outdir, output_filename)
    plt.savefig(output_path)

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
    args = parser.parse_args()

    main(**vars(args))
