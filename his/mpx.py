"""Read DM MPX files to Pandas DataFrames.
Martijn Visser, Deltares, 2016-04

The dataframe has locations as columns and timesteps as index, like so:

   1001      1002      1003
1     0  0.000000  0.053592
2     0  0.514733  0.273920
3     0  1.166179  0.541322
4     0  1.389311  0.632688
5     0  0.570104  0.294276

The index is not a date because unlike HIS files the startdate is not in the file
We could add support for a nice true decade (i.e. not 10 * 86400s) index
as long as the user supplies the startdate.
"""


from datetime import datetime, timedelta
from os.path import getsize
from struct import pack, unpack

import numpy as np
import pandas as pd


def read(mpxfile):
    """Read a mpxfile to a Pandas DataFrame with extra attributes."""
    filesize = getsize(mpxfile)
    with open(mpxfile, "rb") as f:
        _ = f.read(8)
        mapname = f.read(8).rstrip()  # => "lnks"
        timestepkind = f.read(8).rstrip()  # => "decade"

        # if timestepkind == 'decade':
        #     timestep_size_in_seconds = 10 * 86400
        # else:
        #     # just porting from fortran, we can probably support this
        #     raise ValueError('only decade timesteps supported')

        nlocs, steps, series = unpack("hhh", f.read(6))  # => 329, 36, 1
        _ = f.read(10)
        quantity = f.read(40).rstrip()  # => "Debieten in het netwerk"
        unit = f.read(8).rstrip()  # => "m3/s"
        _ = f.read(32)

        nparam = series
        param_ids = []
        for i in range(nparam):
            # ignoring Fortran's UseMpxQuantity
            param_id = f.read(40).rstrip()
            param_ids.append(param_id)

        # read scale definitions and other dummy stuff from MPX header
        _ = f.read(26)  # 13 int16
        _ = f.read(14)  # 14 char
        _ = f.read(40)  # 10 float32
        _ = f.read(8)  # 2 float32
        _ = f.read(32)  # 32 char

        ndone = 240 + series * 40
        nrecsize = 2 + (4 * nlocs)
        nrecnr = 2 + 40 * (7 + series) // nrecsize - 1
        nbytes = nrecnr * nrecsize
        assert ndone == f.tell(), "ndone: {} f.tell() {}".format(ndone, f.tell())
        _ = f.read(nbytes - ndone)
        ndone = nbytes

        # read location ids (numbers)
        loc_ids = []
        for j in range(nlocs):
            k = unpack("h", f.read(2))[0]
            # possible overflow correction
            if k < 0:
                k += 65536
            loc_ids.append(str(k))
        ndone += nlocs * 2
        vara = f.tell()
        assert ndone == f.tell(), "ndone: {} f.tell() {}".format(ndone, f.tell())
        nrecnr = 2 + 40 * (7 + series) // nrecsize
        nbytes = nrecnr * nrecsize
        _ = f.read(nbytes - ndone)

        # read the data
        data = np.zeros((steps, nlocs), np.float32)
        for ts in range(steps):
            _ = f.read(2)  # index (i2) starting as 1, no need to use
            # date = startdate + timedelta(seconds=ts * dt)
            data[ts] = np.fromfile(f, np.float32, nlocs)

        assert filesize - f.tell() == 0

        df = pd.DataFrame(
            data,
            index=range(1, steps + 1),
            columns=loc_ids,
            dtype=np.float32,
            copy=True,
        )
        return df
