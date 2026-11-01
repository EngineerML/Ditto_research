"""s44 case lists: the 40 program questions of each test seed, from the v14 shape oracle."""
import sys

from v14_oracle import shapes

SEEDS = (897500335867350922, 2330430686809638580, 9174290677768307797, 4249690561755544879,
         4137466957291471344, 3374597426558320626, 5704156236337906855)
for seed in SEEDS:
    ids = sorted(shapes(seed))
    with open(f"s44/cases_{seed}.txt", "w") as out:
        out.write("\n".join(ids) + "\n")
    print(seed, len(ids), sorted({shape.label for shape in shapes(seed).values()}))
with open("s44/seeds.txt", "w") as out:
    out.write("\n".join(str(seed) for seed in SEEDS) + "\n")
