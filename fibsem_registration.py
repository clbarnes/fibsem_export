# Albert Cardona 2019-05-31
#
# A script to register FIBSEM serial sections.
# ASSUMES there is only one single image per section.
# ASSUMES all images have the same dimensions and pixel type.
#
# This program is similar to the plugin Register Virtual Stack Slices
# but uses more efficient and densely distributed features,
# and also matches sections beyond the direct adjacent for best stability
# as demonstrated for elastic registration in Saalfeld et al. 2012 Nat Methods.
#
# The program also offers functions to export for CATMAID as N5 format (not multiresolution,
# the multiresolution pyramid can be generated later with a different software).
#
# 1. Extract blockmatching features for every section.
# 2. Register each section to its adjacent, 2nd adjacent, 3rd adjacent ...
# 3. Jointly optimize the pose of every section.
# 4. View the volume as a virtual stack (no image files copied, all transformed on the fly)
# 5. Export volume for CATMAID as N5.

import os, sys
import json
import datetime as dt

here = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.join(here, "scripts")
sys.path.append(os.path.join(scripts_dir, "python/imagej/IsoView-GCaMP/"))

from lib.io import findFilePaths, readFIBSEMdat
from lib.util import numCPUs, syncPrint
from lib.serial2Dregistration import setupImageLoader, viewAligned, export8bitN5, qualityControl
from lib.registration import loadMatrices
from net.imglib2.type.numeric.integer import UnsignedShortType
from net.imglib2 import FinalInterval
from mpicbg.imagefeatures import FloatArray2DSIFT
from ij import IJ
from ij.gui import Roi

CONFIG_NAME = "config.json"


timestamp = dt.datetime.utcnow()


def read_json(path):
    f = open(path)
    d = json.load(f)
    f.close()
    return d


def write_json(object, path):
    f = open(path, "w")
    json.dump(object, path, indent=2, sort_keys=True)
    f.close()


config = read_json(os.path.join(here, "config", CONFIG_NAME))

srcDir = config["srcDatDir"]
csvDir = config["tgtCsvDir"]
exportDir = config["tgtN5Container"]

# srcDir = "/net/fibserver1/raw/Leonardo/" # MUST have an ending slash
# tgtDir = "/net/fibserver1/raw/Leonardo_registered_new"
# tgtDirN5 = "/net/fibserver1/raw/Leonardo_registered_new"
# csvDir = os.path.join(tgtDir, "csvs")

# Recursive search into srcDir for files ending in InLens_raw.tif
filepaths = findFilePaths(srcDir, ".dat")

firstFile = config.get("firstFile")
if firstFile:
    # Remove mouth hooks from processed volume
    startIndex = filepaths.index(os.path.join(firstFile, srcDir))
    filepaths = filepaths[startIndex:]

# Image properties: ASSUMES all images have the same properties
# (While the script an cope with images of different dimensions for registration,
# the visualization and export would need minor adjustments to cope.)
origD = config["originalDimensions"]
dimensions = [origD["width"], origD["height"]]
# dimensions = [11667, 11250]
original_dimensions = dimensions

properties = config["properties"].copy()
properties["img_dimensions"] = dimensions
crop = properties["crop_roi"]
properties["crop_roi"] = Roi(crop["x"], crop["y"], crop["width"], crop["height"])
properties["srcDir"] = srcDir
pixel_types = {
    "uint8": UnsignedShortType
}
properties["pixelType"] = pixel_types[properties["pixelType"]]
clp = properties["CLAHE_params"]
properties["CLAHE_params"] = [clp["blockRadius"], clp["nBins"], clp["slope"]]

badSecs = properties.setdefault("bad_sections", {})
properties["bad_sections"] = {
    int(k): v for k, v in badSecs.iteritems()
}

# properties = {
#  'name': "Leonardo",
#  'img_dimensions': dimensions,
#  'crop_roi': Roi(1296, 2448, 17811, 14616), # x, y, width, height - Pre-crop: right after loading
#  'srcDir': srcDir,
#  'pixelType': UnsignedShortType,
#  'n_threads': 60,
#  'preload': 0, # images to preload ahead of time in the registered virtual stack that opens
#  'invert': True,
#  'CLAHE_params': [200, 256, 3.0], # For viewAligned. Use None to disable. Blockradius, nBins, slope.
#  'use_SIFT': False, # enforce SIFT instead of blockmatching for all sections
#  'precompute': True, # use True at first, False when features and pointmatches exist already
#  'SIFT_validateByFileExists': True, # When True, don't deserialize, only check if the .obj file exists
# # 'bad_sections': {6404: -1,
# #                  8913: -1,
# #                  9719: -1}, # 0-based section indices for keys, and relative index for the value
# }


roi = properties.get("crop_roi", None)
if roi:
  bounds = roi.getBounds()
  dimensions = [bounds.width, bounds.height]


# Validate file sizes:
# header of 1024 bytes
# two 16-bit channel images of width * height
# expected_size = 1024 + original_dimensions[0] * original_dimensions[1] * 2 * 2
# BUT NO: there is a trailer, in addition to a header, of unknow size
#expected_size = 1053794601
expected_size = 1024 + original_dimensions[0] * original_dimensions[1] * config["originalDimensions"]["nChannels"] * 2
# expected_size = 525020417

filepaths2 = []
for idx, path in enumerate(filepaths):

  if os.stat(path).st_size < expected_size:
    print os.stat(path).st_size, "vs expected:", expected_size
    print "Corrupted file path:", path
    properties["bad_sections"].setdefault(idx, -1)

  filepaths2.append(path)
#   else:
#     filepaths2.append(path)

print "Found ", len(filepaths2) - len(filepaths), "corrupted images"
filepaths = filepaths2


# Parameters for blockmatching
# params = {
#  'scale': 0.25, # 10%
#  'meshResolution': 20, # 10 x 10 points = 100 point matches maximum
#  'minR': 0.1, # min PMCC (Pearson product-moment correlation coefficient)
#  'rod': 0.9, # max second best r / best r  # for blockmatching
#  'maxCurvature': 1000.0, # default is 10
#  'searchRadius': 25, # a low value: we expect little translation
#  'blockRadius': 200, # small, yet enough
#  'max_id': 50, # maximum distance between features in image space # for SIFT pointmatches
#  'max_sd': 1.2, # maximum difference in size between features # for SIFT pointmatches
# }
params = config["paramsBlockmatching"]

pSIFT = config["paramsSIFT"]

# Parameters for SIFT features, in case blockmatching fails due to large translation or image dimension mistmatch
paramsSIFT = FloatArray2DSIFT.Param()
# paramsSIFT.fdSize = 8 # default is 4
# paramsSIFT.fdBins = 8 # default is 8
paramsSIFT.fdSize = pSIFT["fdSize"]
paramsSIFT.fdBins = pSIFT["fdBins"]
paramsSIFT.maxOctaveSize = pSIFT.get("maxOctaveSize") or int(max(2048, dimensions[0] * params["scale"]))
# paramsSIFT.maxOctaveSize = 2048  # int(max(2048, dimensions[0] * params["scale"]))
paramsSIFT.steps = pSIFT["steps"]
paramsSIFT.minOctaveSize = int(paramsSIFT.maxOctaveSize / pow(2, paramsSIFT.steps))
paramsSIFT.initialSigma = pSIFT["initialSigma"]
# paramsSIFT.initialSigma = 1.6 # default 1.6

paramsTileConfiguration = config["paramsTileConfiguration"]
# Parameters for computing the transformation models
# paramsTileConfiguration = {
#   "n_adjacent": 3, # minimum of 1; Number of adjacent sections to pair up
#   "maxAllowedError": 0, # Saalfeld recommends 0
#   "maxPlateauwidth": 200, # Like in TrakEM2
#   "maxIterations": 1000, # Saalfeld recommends 1000 -- here, 2 iterations (!!) shows the lowest mean and max error for dataset FIBSEM_L1116
#   "damp": 1.0, # Saalfeld recommends 1.0, which means no damp
# }




# Dimensions of the ROI to show once the registration completes.
# Default: show all. Adjust to show only a cropped area.
x0 = int(dimensions[0]//2) # X coordinate of the first pixel to show
y0 = int(dimensions[1]//2) # Y coordinate of the first pixel to show
x1 = x0 + 500 # dimensions[0] -1 # X coordinate of the last pixel to show
y1 = y0 + 500 # dimensions[1] -1 # Y coordinate of the last pixel to show
syncPrint("Crop to: x=%i y=%i width=%i height=%i" % (x0, y0, x1 - x0 + 1, y1 - y0 + 1))


# CORRECTION after having exported once with 3 artifactual images:
# 6404: high mag
# 8913: high mag
# 9719: corrupted content

# Cope with artifactual images: replace their filepaths with that of another section
to_replace = {filepaths[index]: filepaths[index + inc]
              for index, inc in properties.get("bad_sections", {}).iteritems()}

# Adjust image loader as needed:
if filepaths[0].endswith(".dat"):
  def loadFn(filepath):
    global properties, to_replace

    filepath = to_replace.get(filepath, filepath)

    imp = readFIBSEMdat(filepath, channel_index=0, asImagePlus=True, toUnsigned=True)[0]
    roi = properties.get("crop_roi", None)
    if roi:
      ip = imp.getProcessor()
      ip.setRoi(roi)
      imp.setProcessor(ip.crop())
    return imp
  syncPrint("Using io.readFIBSEMdat to read image files.")
  loader = loadFn
  setupImageLoader(loader)
else:
  # TODO doesn't handle ROI, to_replace, etc.
  loader = IJ.loadImage
  syncPrint("Using IJ.loadImage to read image files.")


# Triggers the whole alignment and ends by showing a virtual stack of the aligned sections.
# Crashware: can be restarted anytime, will resume from where it left off.
if config["viewAlignment"]:
  imp = viewAligned(filepaths, csvDir, params, paramsSIFT, paramsTileConfiguration, properties,
                    FinalInterval([x0, y0], [x1, y1]))
  # Open a sortable table with 3 columns: the image filepath indices and the number of pointmatches
  qualityControl(filepaths, csvDir, params, properties, paramsTileConfiguration, imp=imp)


def update_attributes(attrs, container_root, object_name=None):
    reserved = {"dimensions", "dataType", "blockSize", "compression", "n5"}
    safe_attrs = {k: v for k, v in attrs.iteritems() if k not in reserved}

    if len(safe_attrs) < len(attrs):
        print "Refusing to overwrite essential attributes"

    if object_name:
        object_name = object_name.strip("/")
    dirpath = os.path.join(container_root, object_name) if object_name else container_root

    attr_path = os.path.join(dirpath, "attributes.json")
    if os.path.isfile(attr_path):
        d = read_json(attr_path)
    else:
        d = dict()
    d.update(safe_attrs)
    write_json(d, attr_path)


# When the alignment is good enough, then export as N5 by swapping "False" for "True" below:


if config["exportN5"]:

  # Ignore ROI: export the whole volume
  dimensions = original_dimensions
  properties["crop_roi"] = None

  # Write the whole volume in N5 format
#   name = properties["name"] # srcDir.split('/')[-2]
  group_name = config["n5"]["tgtN5Group"]
  ds_name = group_name.rstrip("/") + "/" + "s0"
  exportDir = config["n5"]["tgtN5Container"]
  # Export ROI:
  # x=864 y=264 width=15312 h=17424
  interval = FinalInterval([0, 0], [dimensions[0] -1, dimensions[1] -1])


  export8bitN5(filepaths,
               loader,
               dimensions,
               loadMatrices("matrices", csvDir), # expects matrices.csv file to exist already
               ds_name,
               exportDir,
               interval,
               gzip_compression=0, # Don't use compression: less than 5% gain, at considerable processing cost
               invert=True,
               CLAHE_params=properties["CLAHE_params"],
               n5_threads=properties["n_threads"],
               block_size=config["blockSize"]) # ~4 MB per block

  resolution = {
      "resolution": config["n5"]["resolution"],
      "units": [config["n5"]["resolutionUnit"]] * 3
  }
  group_metadata = {
      "downsamplingFactors": [[1, 1, 1]],
      "metadata": config["metadata"],
      **resolution
  }
  update_attributes(group_metadata, exportDir, group_name)
  update_attributes(
      {
          "exportConfig": config,
          "exportTimestampUTC": timestamp.isoformat(),
          "badSections": {str(k): v for k, v in properties["bad_sections"].iteritems()},
          **resolution
      },
      exportDir, ds_name
  )
