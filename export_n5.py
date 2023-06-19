#!/usr/bin/env jython
import os, sys

here = os.path.dirname(os.path.abspath(__file__))
utils_dir = os.path.join(here, "utils")
sys.path.append(utils_dir)

from fibsem_registration import (
    original_dimensions,
    properties,
    CONFIG,
    FinalInterval,
    export8bitN5,
    filepaths,
    loader,
    loadMatrices,
    csvDir,
    update_attributes,
    timestamp,
)

if not os.path.isdir(csvDir) or not os.listdir(csvDir):
    raise RuntimeError("CSV dir is nonexistent or empty. Run view_alignment.py first.")

# Ignore ROI: export the whole volume
dimensions = original_dimensions
properties["crop_roi"] = None

# Write the whole volume in N5 format
#   name = properties["name"] # srcDir.split('/')[-2]
group_name = CONFIG["n5"]["tgtN5Group"]
ds_name = group_name.rstrip("/") + "/" + "s0"
exportDir = CONFIG["n5"]["tgtN5Container"]
# Export ROI:
# x=864 y=264 width=15312 h=17424
interval = FinalInterval([0, 0], [dimensions[0] - 1, dimensions[1] - 1])

export8bitN5(
    filepaths,
    loader,
    dimensions,
    loadMatrices("matrices", csvDir),  # expects matrices.csv file to exist already
    ds_name,
    exportDir,
    interval,
    gzip_compression=0,  # Don't use compression: less than 5% gain, at considerable processing cost
    invert=True,
    CLAHE_params=properties["CLAHE_params"],
    n5_threads=properties["n_threads"],
    block_size=CONFIG["blockSize"],
)  # ~4 MB per block

resolution = {
    "resolution": CONFIG["n5"]["resolution"],
    "units": [CONFIG["n5"]["resolutionUnit"]] * 3,
}
group_metadata = {
    "downsamplingFactors": [[1, 1, 1]],
    "metadata": CONFIG["metadata"],
    **resolution,
}
update_attributes(group_metadata, exportDir, group_name)
update_attributes(
    {
        "exportConfig": CONFIG,
        "exportTimestampUTC": timestamp.isoformat(),
        "badSections": {str(k): v for k, v in properties["bad_sections"].iteritems()},
        **resolution,
    },
    exportDir,
    ds_name,
)
