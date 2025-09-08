# code copied from https://gitlab.com/visr/his-python, commit 45bced49, 2021-06-09
# since that is not a registered python package

import configparser
from datetime import datetime, timedelta
from os.path import getsize
from pathlib import Path
from struct import unpack
from typing import List, Set, Dict, Tuple, Optional, Callable

import numpy as np
import xarray as xr


def _update_long(lst, config, section):
    if section in config:
        # subtract 1 to get a 0 based index for the location
        long_map = {int(k) - 1: v for (k, v) in config[section].items()}
        for i, long_name in long_map.items():
            lst[i] = long_name
    return lst

def _update_illegal_characters(lst)-> List:
    """
    remove illegal characters from list items to comply to netcdf standards
    :param lst: input items holding illegal characters
    :return: List of output items where illegal characters are replaced by _ and spaces are removed
    """
    newlst = []
    for i in lst:
        # assign long name while correcting for characters that are illegal in netcdf
        # not that , and # can be acceptable
        newlst.append(i.replace(':','_').replace('.','_').replace('/','_').replace('- ', 'out_').replace('+ ', 'in_').
                replace(',','_').replace('(','_').replace(')','_').replace('[','_').replace(']','_').
                      replace('<', 'lt_').replace('>', 'gt_').replace('%', 'pct').replace('#', 'Nr').replace(' ',''))
    return newlst

def _get_units(long_params, legal_params)-> Dict:
    """
    Obtain the unit from the his parameter

    :param long_params: parameter to derive unit from
    :param legal_params: parameter used as key in output dictionary
    :return: output dictionary
    """
    newdct = {}
    for i, x in zip(long_params, legal_params):
        if '(' in i:
            newdct[x] = i.split('(')[1].split(')')[0]
        elif '[' in i:
            newdct[x] = i.split('[')[1].split(']')[0]
        else: '-'
    return newdct

def readhis(hisfile, hia=True):
    """
    Read a hisfile to a xarray.Dataset ready for export to Fews

    If uses the location numbers with the featuretype as prefix
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

    if Path(hisfile).with_suffix(".hia").is_file():
        config = configparser.ConfigParser(interpolation=None)
        config.read(Path(hisfile).with_suffix(".hia"))
        # always use long parameter names
        params = _update_long(params, config, "Long Parameters")
    legal_params = _update_illegal_characters(params)
    ftype = hisfile.stem.lstrip('__')
    # use location position unless hia=true (for cultivations only) then use the long locations
    if hia and Path(hisfile).with_suffix(".hia").is_file():
        locs = _update_long(locs, config, "Long Locations")
        locs = _update_illegal_characters(locs)
        # use long names without spaces and only single '_' to allow standardized idmapping
        locs = [x.replace('_____','_').replace('____','_').replace('___','_').replace('__','_').replace(' ','') for x in locs]
        locids=[ftype + str(x) for x in locs]
    else:
        # use numeric location ids instead of name that are non-guaranteed to be unique
        locids = [ftype + str(x) for x in locnrs]


    ds = xr.Dataset(
        {
            param: (["time", "station"], data[i, ...])
            for (i, param) in enumerate(legal_params)
        },
        coords={
            "time": dates,
            "station": locids,
        },
        attrs=dict(title=header, source='Ribasim 7 engine', references='http:///www.deltares.nl/ribasim',
               scu=dt, t0=str(startdate)),

    )

    # add meta data for CF-convention/Fews
    ds['station'].attrs['long_name'] = 'station'
    ds['station'].attrs['cf_role'] = 'timeseries_id'
    param_units = _get_units(long_params=params, legal_params=legal_params)

    for u,par in zip(param_units, params):
        ds[u].attrs['long_name'] = par
        ds[u].attrs['units'] = param_units[u]

    return ds
