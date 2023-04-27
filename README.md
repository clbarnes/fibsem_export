# fibsem_export

Exporting registered N5 volumes from the Cardona lab's Jeiss micrographs.

This repo was originally created based on the export configuration for "leonardo", around 2023-02-03.

## Process

Aligns a directory tree of `.dat` files using elastic block matching (falling back to SIFT in particularly bad cases), correcting contrast with CLAHE.
Then, exports to 8-bit N5, storing information about the volume and the export process as attributes.

"Bad" sections (manually identified as garbage, or automatically identified truncated .dat files) are replaced with the values from a neighboring section.

## Usage

Clone this repo, **including the submodule** (this will also pull in the utilities in [Albert's scripts](https://github.com/acardona/scripts)), and make your own branch.

```sh
git clone --recursive https://github.com/clbarnes/fibsem_export
cd fibsem_export
git checkout -b my_export_name
```

Then, modify the `config/config.json` file, with help from `config/README.md` (not all fields are documented, as some are fairly self-explanatory).
If you *need* multiple configurations in one place, you can copy the JSON file and change the name in `utils/fibsem_registration.py`, but I recommend against it.

### First use

Ensure that the JSON configuration file's `"viewAlignment"` is set to `true` the first time you run it.
This is necessary to produce some intermediate artifacts the export will later rely on.
You will probably also want to ensure that `"n5"."exportN5` is `false` for this run, even if you are just re-running a previously successful configuration.

Use [FIJI](https://imagej.net/software/fiji/)'s python script runner to run `fibsem_registration.py`.

Modify the config file if any parameters need tweaking.

### Finalising

Once you're happy with the alignment:

[Stage (add)](https://www.w3schools.com/git/git_staging_environment.asp?remote=github) and [commit](https://www.w3schools.com/git/git_commit.asp?remote=github) your changes to git so that you have a forever-accessible snapshot of the state of the config and code.
You might also want to tag and push it to a fork, but this isn't a git tutorial ([this is](https://missing.csail.mit.edu/2020/version-control/)).

Change the config file's `"viewAlignment"` to `false` and `"n5"."exportN5"` to `true`, and run the script again to export the volume as N5.

The configuration will be stored in the N5 so that anyone can see the parameters used for it.

If you have made changes to the actual script and think they would be beneficial to others, raise a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests) to add it to the mainline repository.

### Scale pyramid

The recommended tool is [saalfeldlab/n5-spark](https://github.com/saalfeldlab/n5-spark).
Install according to the instructions there, using the "local machine" configuration.

The easiest way to control every step of the downsampling (e.g. changing the factors so that voxels become isotropic) is to write a script with successive calls to `n5-downsample.py` for each level.

This repo also contains a python script (`scripts/python/add_downsampling.py`) to update the multiscale group's metadata with the given downsampling factors.
Run this after the n5-spark script has created the new dataset.

```sh
#!/bin/bash

# whole-process configuration
N5_SPARK_PATH=/path/to/n5-spark
FIBSEM_EXPORT_PATH=/path/to/this/repo

tgtN5Container=/path/to/my/container.n5
tgtN5Group=v1/raw

# per-downscale configuration
CURRENTSCALE=0
NEXTSCALE=1
DOWNSAMPLING='2,2,2'

# downsample
$N5_SPARK_PATH/startup-scripts/n5-downsample.py -n $tgtN5Container -i $tgtN5Group/s$CURRENTSCALE -o $tgtN5Group/s$NEXTSCALE -f $DOWNSAMPLING

# update metadata
python3 $FIBSEM_EXPORT_PATH/scripts/python/add_downsampling.py $tgtN5Container $tgtN5Group $NEXTSCALE $DOWNSAMPLING

# next iteration
CURRENTSCALE=$NEXTSCALE
NEXTSCALE=$((NEXTSCALE+1))
# change DOWNSAMPLING too if you need

# run n5-downsample.py and add_downsampling.py lines again
# ... repeat ad nauseam
```

## Updating Albert's scripts

This repo is tied to a specific version of the scripts, for explicitness/ reproducibility reasons, but it's easy to update it with changes.

You can `cd` into the `scripts` directory and jump through its git history (branches, tags, pulling from the remote etc.) at your leisure.
If you're just looking to pull the latest changes from the top directory,

```sh
git submodule update --recursive --remote
```

Then (in the top directory) `git add utils/acardona_scripts` to register those changes with your project.

If you need to modify the scripts yourself, you should create a branch of the submodule (so that subsequent submodule updates don't wipe out your changes).
Make sure that these changes get pushed somewhere too, otherwise you won't be able to use them the next time you check out this repository.
