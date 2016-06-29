#!/usr/bin/env python
from __future__ import print_function

import mantid.simpleapi

import matplotlib
matplotlib.use("agg")
import matplotlib.pyplot as plt

import numpy as np
np.seterr(all='ignore')

import warnings
warnings.filterwarnings('ignore',module='numpy')

def main(filename, outdir):
    w = mantid.simpleapi.Load(filename)

    wi = mantid.simpleapi.Integration(w)

    data = wi.extractY().reshape(-1,8,256).T

    data2 = data[:,[0,4,1,5,2,6,3,7],:]

    data2 = data2.transpose().reshape(-1,256)

    X, Y = np.meshgrid(np.arange(192)+1, np.arange(256)+1)

    Z = np.ma.masked_where(data2<1, data2)

    plt.pcolormesh(X, Y, np.log(Z.transpose()))
    plt.ylim([0, 256])
    plt.xlim([0, 192])
    plt.xlabel('Tube')
    plt.ylabel('Pixel')

    output_filename = "EQSANS_{}_autoreduced.png".format(w.getRunNumber())
    output_path = os.path.join(outdir, output_filename)
    plt.savefig(output_path)

if __name__ == "__main__":
    import argparse
    import os

    def path_exists(path):
        if not os.path.exists(path):
            raise argparse.ArgumentTypeError("{} does not exist".format(path))
        return path

    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=path_exists)
    parser.add_argument('outdir', type=path_exists)
    args = parser.parse_args()

    main(**vars(args))
