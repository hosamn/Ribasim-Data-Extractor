"""Reads and writes SOBEK HIS files.
Martijn Visser, Deltares, 2014-06

changelog:
2016/09/07: Erwin Meijers:
* Changed bytes to strings (times, locs, params for Python3)
* replaced xrange by range
"""

import configparser
from datetime import datetime, timedelta
from os.path import getsize
from pathlib import Path
from struct import pack, unpack

import numpy as np
import pandas as pd
import xarray as xr


def _update_long(lst, config, section):
    if section in config:
        # subtract 1 to get a 0 based index for the location
        long_map = {int(k) - 1: v for (k, v) in config[section].items()}
        for i, long_name in long_map.items():
            lst[i] = long_name
    return lst


def read(hisfile, hia=True):
    """
    Read a hisfile to a xarray.Dataset

    If hia is True, it will use the long location names from the .hia sidecar file
    if it exists.
    """
    filesize = getsize(hisfile)
    if filesize == 0:
        raise ValueError(f"HIS file is empty: {hisfile}")
    with open(hisfile, "rb") as f:
        header = f.read(120).decode("utf-8")
        timeinfo = f.read(40).decode("utf-8")
        datestr = timeinfo[4:14].replace(" ", "0") + timeinfo[14:23]
        startdate = datetime.strptime(datestr, "%Y.%m.%d %H:%M:%S")
        try:
            dt = int(timeinfo[30:-2])  # assumes unit is seconds
        except ValueError:
            # in some RIBASIM his files the s is one place earlier
            dt = int(timeinfo[30:-3])
        noout, noseg = unpack("ii", f.read(8))
        notim = int(
            ((filesize - 168 - noout * 20 - noseg * 24) / (4 * (noout * noseg + 1)))
        )
        params = [(f.read(20).rstrip()).decode("utf-8") for _ in range(noout)]
        locnrs, locs = [], []
        for i in range(noseg):
            locnrs.append(unpack("i", f.read(4))[0])
            locs.append((f.read(20).rstrip()).decode("utf-8"))
        dates = []
        data = np.zeros((noout, notim, noseg), np.float32)
        for t in range(notim):
            ts = unpack("i", f.read(4))[0]
            date = startdate + timedelta(seconds=ts * dt)
            dates.append(date)
            for s in range(noseg):
                data[:, t, s] = np.fromfile(f, np.float32, noout)

    if hia:
        # if there is a hia file next to the his, use the long locations
        hia_path = Path(hisfile).with_suffix(".hia")
        if hia_path.is_file():
            config = configparser.ConfigParser(interpolation=None)
            config.read(hia_path)
            locs = _update_long(locs, config, "Long Locations")
            params = _update_long(params, config, "Long Parameters")

    ds = xr.Dataset(
        {
            param: (["time", "station"], data[i, ...])
            for (i, param) in enumerate(params)
        },
        coords={
            "time": dates,
            "station": locs,
        },
        attrs=dict(header=header, scu=dt, t0=startdate),
    )
    return ds


def write(hisfile, ds):
    """Writes an xarray.Dataset with extra attributes to a hisfile."""
    with open(hisfile, "wb") as f:
        header = ds.attrs["header"]
        scu = ds.attrs["scu"]
        t0 = ds.attrs["t0"]
        f.write(header.ljust(120)[:120].encode("ascii"))  # enforce length
        t0str = t0.strftime("%Y.%m.%d %H:%M:%S")
        timeinfo = "T0: {}  (scu={:8d}s)".format(t0str, scu)
        f.write(timeinfo.encode("ascii"))
        noout = len(ds)
        notim, noseg = ds.time.size, ds.station.size
        f.write(pack("ii", noout, noseg))
        params = np.array(list(ds.keys()), dtype="S20")
        params = np.char.ljust(params, 20)
        params.tofile(f)
        locs = np.array(ds.station, dtype="S20")
        locs = np.char.ljust(locs, 20)
        for locnr, loc in enumerate(locs):
            f.write(pack("i", locnr))
            f.write(loc)
        da = ds.to_array()
        assert da.dims != ("variable", "time", "station")
        data = da.values.astype(np.float32)
        for t, date in enumerate(ds.time.values):
            date = pd.Timestamp(date).to_pydatetime()
            ts = int((date - t0).total_seconds() / scu)
            f.write(pack("i", ts))
            for s in range(noseg):
                data[:, t, s].tofile(f)
        countmsg = "hisfile written is not the correct length"
        assert f.tell() == 160 + 8 + 20 * noout + (4 + 20) * noseg + notim * (
            4 + noout * noseg * 4
        ), countmsg
