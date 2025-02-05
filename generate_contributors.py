# -*- coding: utf-8 -*-

from subprocess import check_output
from copy import deepcopy

remove_names = ["none"]
replace_contributors =   {"CRImier": "CRImier (Arsenijs)",
                          "ahub": "monsieur_h",
                          "monsieurh": "monsieur_h",
                          "Arsenijs": "CRImier (Arsenijs)",
                          "samkaufman01": "Sam Kaufman",
                          "crimier": "CRImier (Arsenijs)",
                          "kylemoran138": "KyleMoran138",
                          "Ser2808": "Serge Spraiter",
                          "CrunchBang LiveUser": "CRImier (Arsenijs)",
                          "Zero Phone": "Unnamed contributor",
                          "LouisPi": "Louis Parkerson",
                          "Louis Pi": "Louis Parkerson"}


add_contributors = [[10, "Serge Spraiter"], [5, "piajesse"]]

output = check_output(["git", "shortlog", "--numbered", "--summary", "--all"])
lines = filter(None, [line.strip() for line in output.split('\n')])
contributors = [line.split("\t", 1) for line in lines]
contributors = [[int(n), name.strip()] for n, name in contributors]
for c in add_contributors:
    contributors.append(c)
for cnum, cname in deepcopy(contributors):
    if cname in replace_contributors:
        replacement_name = replace_contributors[cname]
        for i, info in enumerate(deepcopy(contributors)):
            num, name = info
            if name == replacement_name:
                contributors[i][0] += cnum
                contributors.remove([cnum, cname])
                break
        else:
            contributors.remove([cnum, cname])
            contributors.append([cnum, replacement_name])
contributors = list(reversed(sorted(contributors)))
contributor_names = [name for _, name in contributors if name not in remove_names]


with open("CONTRIBUTORS.md", 'w') as f:
    f.write("#ZPUI project contributors\n\n")
    for name in contributor_names:
        f.write(" - {}\n".format(name))
