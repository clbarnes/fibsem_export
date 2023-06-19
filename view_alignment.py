#!/usr/bin/env jython
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.join(here, "utils")
sys.path.append(utils_dir)

from fibsem_registration import (
    viewAligned,
    params,
    paramsSIFT,
    paramsTileConfiguration,
    properties,
    x0,
    y0,
    x1,
    y1,
    filepaths,
    properties,
    qualityControl,
    FinalInterval,
    csvDir,
)

# Triggers the whole alignment and ends by showing a virtual stack of the aligned sections.
# Crashware: can be restarted anytime, will resume from where it left off.
imp = viewAligned(
    filepaths,
    csvDir,
    params,
    paramsSIFT,
    paramsTileConfiguration,
    properties,
    FinalInterval([x0, y0], [x1, y1]),
)
# Open a sortable table with 3 columns: the image filepath indices and the number of pointmatches
qualityControl(filepaths, csvDir, params, properties, paramsTileConfiguration, imp=imp)
