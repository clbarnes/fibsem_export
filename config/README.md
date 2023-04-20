# Config

Configuration for particular exports are found here.

They are in [JSON format](https://en.wikipedia.org/wiki/JSON#Syntax).

This documentation was initially derived from comments in the underlying code.

## Configuration

- `firstFile`: Skip all images before this one (relative to `srcDatDir`); `null` to use first available image.
- `originalDimensions`: Width and height of the images in the .dat file.
- `expectedFileNBytes`: 1024 bytes of header, image data (e.g. 2x16bit channels of size `width*height`), plus possibly some padding 0s, plus a binary footer of indeterminate size.
- `viewAlignment`: Whether to show the virtual stack of the aligned sections (switch to `false` when alignment is good enough). Must be run with `true` at least once (with `properties.precompute = true`) to generate point match CSVs before N5 can be exported.

### `n5`

- `exportN5`: Whether to export the aligned N5 (switch to `true` when alignment is good enough).
- `tgtN5Container`: Should be a directory ending with `.n5`
- `tgtN5Group`: Name of the output group within `tgtN5Container` which will become a scale pyramid (may include intervening groups). The dataset will be the base of the pyramid: `${tgtN5Group}/s0`.
- `blockSize`: In pixels; preferably 2-4 MB per block, isotropic in nm space, and ideally power-of-two in each dimension.
- `resolution`: In real space, the size of each voxel.
- `resolutionUnit`: SI-prefix + `m` (e.g. `"nm"`).

### `metadata`

Information about the dataset.
Fill in as much as you possibly can.

- `attribution`: If someone in the future came across this dataset, who should they ask about it? Sample prep, imaging, export, intended users etc.

### `properties`

- `crop_roi`: Crop to apply to every image immediately upon loading; use `null` to disable. Only applies to viewing, not to N5 export.
- `pixelType`: `"uint8"` for unsigned 8-bit integer.
- `CLAHE_params`: For viewAligned; use `null` to disable.
- `use_SIFT`: force SIFT instead of blockmatching for all sections.
- `precompute`: `true` to generate feature/ pointmatch CSVs, `false` when they already exist.
- `preload`: Images to preload ahead of time in the registered virtual stack that opens.
- `SIFT_validateByFileExists`: When `true`, don't deserialize, only check if the .obj file exists
- `badSections`: Mapping from 0-based section index starting from `firstFile` if given (as a string) to relative index (i.e. which slice the missing slice should be replaced with; usually `-1`). Empty (`{}`) to export all sections. This will be expanded with any sections where the file seems to have been truncated.

### `paramsBlockmatching`

- `scale`: 10%.
- `meshResolution`: 10x10 points = 100 point matches maximum.
- `minR`: Minimum Pearson product-moment correlation coefficient (PMCC).
- `rod`: Max second best `r` / best `r`.
- `maxCurvature`: Default is 10.
- `searchRadius`: A low value: we expect little translation.
- `blockRadius`: Small, yet enough.
- `max_id`: Maximum distance between features in image space for SIFT pointmatches.
- `max_sd`: Maximum difference in size between features for SIFT pointmatches

### `paramsSIFT`

Parameters for SIFT features, in case blockmatching fails due to large translation or image dimension mismatch.

- `fdSize`: Default is 4.
- `fdBins`: Default is 8.
- `maxOctaveSize`: If `null`, guessed from dimensions and scale.
- `initialSigma`: Default is 1.6.

### `paramsTileConfiguration`

Parameters for computing the transformation models.

- `n_adjacent`: Minimum of 1; number of adjacent sections to pair up.
- `maxAllowedError`: Saalfeld recommends 0.
- `maxPlateauWidth`: Like in TrakEM2.
- `maxIterations`: Saalfeld recommends 1000; here 2 iterations shows the lowest mean and max error for dataset FIBSEM_L1116.
- `damp`: Saalfeld recommends 1.0, which means no damp.
