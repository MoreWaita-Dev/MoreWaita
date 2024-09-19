import argparse
import re
from os import listdir, readlink
from os.path import isfile, join, islink
from graphlib import TopologicalSorter


parser = argparse.ArgumentParser(
        description=(
            "Update regular files and groups"
            " of links in meson.build file."
        )
    )
parser.add_argument(
    "readdir",
    metavar="readdir",
    type=str,
    nargs="?",
    default="."
)
args = parser.parse_args()

DIR: str = args.readdir
# read all files from directory
files = sorted(listdir(DIR))
files.remove("meson.build")


regular_files: list[str] = []
link_files: list[str] = []

for file in files:
    file_: str = join(DIR, file)
    # filter out regular files
    if isfile(join(file_)) and not islink(file_):
        regular_files.append("    '{}',\n".format(file))
    # filter out link files
    elif isfile(join(file_)) and islink(file):
        link_files.append(file)

# dictonary for grouping files and their links
groups: dict = {}
for link in link_files:
    groups.setdefault(
        readlink(
            join(args.readdir, link)
        ), []
    ).append(link)

# sort groups topologically
# that way chain links will be created in correct order
ts = TopologicalSorter(groups)

# get a list of tuples so the order is maintained
# when pairing sorted keys with their values
sorted_groups: list[tuple[str, str]] = []
for file in ts.static_order():
    if file in groups:
        sorted_groups.append((file, groups[file]))

# iterate over all groups
# reverse the order of groups so
# first the dependencies are created
new_link_lines = []
for file, links in reversed(sorted_groups):
    # print a comment line indicating a
    # group of links (file that they link to)
    new_link_lines.append("    "{}": [\n".format(file))
    for link in links:
        # print a line for each link file
        new_link_lines.append("        "{}",\n".format(link))
    new_link_lines.append("    ],\n")

reg_lines = None
link_lines = None

# match lines in regular and link segments
r = re.compile(
    (
        r"^((?:.*\n)+    # DO NOT REMOVE: Begining of reg"
        r"ular segment\n)((?:.+\n)*)(    # DO NOT REMOVE:"
        r" End of regular segment\n(?:.*\n)+    # DO NOT "
        r"REMOVE: Begining of link segment\n)((?:.+\n)*)("
        r"    # DO NOT REMOVE: End of link segment\n(?:.*\n)+)$"
    ),
    re.MULTILINE
)

with open(join(args.readdir, "meson.build"), "r") as f:
    match_lines = r.match("".join(f.readlines()))

if match_lines:
    with open(join(args.readdir, "meson.build"), "w") as f:
        f.write(match_lines.group(1))
        f.write("".join(regular_files))
        f.write(match_lines.group(3))
        f.write("".join(new_link_lines))
        f.write(match_lines.group(5))
