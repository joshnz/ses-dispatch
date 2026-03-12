import re


def extract_keywords(description: str) -> list[str]:
    desc = description.lower()
    keywords = []
    if re.search(r"tree|branch|limb|trunk", desc):
        keywords.append("chainsaw")
    if re.search(r"flood|water|rising|drain|sandbag", desc):
        keywords.extend(["pump", "sandbagging"])
    if re.search(r"tarp|roof|tile|window|cover", desc):
        keywords.append("tarp")
    if re.search(r"road|traffic|clearance|block", desc):
        keywords.append("road_clearance")
    if re.search(r"large tree|power line|trapped|lean.*over|collapse|structure", desc):
        keywords.append("heavy_duty")
    return list(set(keywords))
