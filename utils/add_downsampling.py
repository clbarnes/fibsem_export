#!/usr/bin/env python3
import json
import os
from pathlib import Path
from argparse import ArgumentParser
import logging

logger = logging.getLogger(__name__)


def resolved_path(s: str):
    return Path(s).resolve()


def group_name(s: str):
    return s.strip(os.path.sep).strip("/")


def parse_downsampling(s: str):
    els = s.split(",")
    if len(els) == 1:
        return int(els[0])
    return [int(el) for el in els]


def zip_mult(prev_downscale, new_downscale):
    if isinstance(new_downscale, int):
        new_downscale = [new_downscale] * len(prev_downscale)
    return [lft*rt for lft, rt in zip(prev_downscale, new_downscale)]


def check_arrays_exist(group_path: Path, new_scale: int):
    for scale in range(0, new_scale + 1):
        attrs_path = group_path / f"s{scale}/attributes.json"
        if not attrs_path.is_file():
            raise FileNotFoundError(f"Dataset attributes not found at {attrs_path}")


def add_downscale(group_path: Path, new_scale: int, downscaling):
    attrs_path = group_path / "attributes.json"
    attrs = json.loads(attrs_path.read_text())
    dsf = attrs["downsamplingFactors"]
    if len(dsf) != new_scale:
        raise RuntimeError(f"Expected {new_scale} existing elements in downsamplingFactors, got {len(dsf)}")
    total_downscale = zip_mult(dsf[-1], downscaling)
    dsf.append(total_downscale)
    s = json.dumps(attrs, indent=2, sort_keys=True)
    attrs_path.write_text(s)

    try:
        units = attrs["units"]
        resolution = attrs["resolution"]
    except KeyError:
        logger.info(f"Group has no resolution information, not writing to dataset s{new_scale} metadata")
        return

    new_res = zip_mult(resolution, total_downscale)

    ds_attr_path = group_path / f"s{new_scale}/attributes.json"
    ds_attrs = json.loads(ds_attr_path.read_text())
    if "units" in ds_attrs or "resolution" in ds_attrs:
        logger.info(f"Resolution info already found in dataset s{new_scale}, not overwriting")
        return

    ds_attrs["units"] = units
    ds_attrs["resolution"] = new_res
    s2 = json.dumps(attrs, indent=2, sort_keys=True)
    ds_attr_path.write_text(s2)


def main(args=None):
    logging.basicConfig(level=logging.INFO)
    parser = ArgumentParser()
    parser.add_argument("container", type=resolved_path, help="Path to N5 container")
    parser.add_argument("group", type=group_name, help="Qualified name of multiscale N5 group")
    parser.add_argument("newscale", type=int, help="The scale level of the new array")
    parser.add_argument("downsampling", type=parse_downsampling, help="Single-step downsampling as comma-separated integers")

    parsed = parser.parse_args(args)

    group_path = parsed.container / parsed.group

    check_arrays_exist(group_path, parsed.newscale)

    add_downscale(group_path, parsed.newscale, parsed.downsampling)


if __name__ == "__main__":
    main()
