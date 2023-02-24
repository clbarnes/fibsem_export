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
If you *need* multiple configurations in one place, you can copy the JSON file and change the name in `fibsem_registration.py`, but I recommend against it.

Use FIJI's python script runner to run `fibsem_registration.py`.
Modify the JSON configuration file if any parameters need tweaking.

### Finalising

Once you're happy with the alignment:

[Stage (add)](https://www.w3schools.com/git/git_staging_environment.asp?remote=github) and [commit](https://www.w3schools.com/git/git_commit.asp?remote=github) your changes to git so that you have a forever-accessible snapshot of the state of the config and code.
You might also want to tag and push it to a fork, but this isn't a git tutorial ([this is](https://missing.csail.mit.edu/2020/version-control/)).

Change the config file's `"viewAlignment"` to `false` and `"n5"."exportN5"` to `true`, and run the script again to export the volume as N5.

The configuration will be stored in the N5 so that anyone can see the parameters used for it.

If you have made changes to the actual script and think they would be beneficial to others, raise a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests) to add it to the mainline repository.

## Updating Albert's scripts

This repo is tied to a specific version of the scripts, for explicitness/ reproducibility reasons, but it's easy to update it with changes.

You can `cd` into the `scripts` directory and jump through its git history (branches, tags, pulling from the remote etc.) at your leisure.
If you're just looking to pull the latest changes from the top directory,

```sh
git submodule update --recursive --remote
```

Then (in the top directory) `git add scripts` to register those changes with your project.

If you need to modify the scripts yourself, you should create a branch of the submodule (so that subsequent submodule updates don't wipe out your changes).
Make sure that these changes get pushed somewhere too, otherwise you won't be able to use them the next time you check out this repository.
