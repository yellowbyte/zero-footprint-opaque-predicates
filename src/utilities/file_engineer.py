import os


def remove_starting_from(filepath, to_remove):
    """
    For each line of file at `filepath`, remove `to_remove` 
    from the line and everything after
    """
    content = get_file_content(filepath, return_type="list")
    filtered = list()
    for l in content:
        remove_loc = l.find(to_remove)
        if remove_loc == -1:
            filtered.append(l)
        else:
            filtered.append(l[:remove_loc])
    with open(filepath, "w") as f:
        f.write("\n".join(filtered))


def get_file_content(filepath, return_type="list"):
    """
    Bring content of file at `filepath` to memory
    """
    filtered = list()
    with open(filepath, "r") as f:
        if return_type == "list":
            content = [l.rstrip("\n") for l in f.readlines()]
        else:
            content = f.read()
    return content


def get_filepath_ext(filepath, ext):
    """
    Change a file specified at `filepath` to `ext`
    """
    dirname = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    cur_ext_loc = filename.find(".")
    if cur_ext_loc == -1:
        return os.path.join(dirname, filename+"."+ext)
    return os.path.join(dirname, filename[:cur_ext_loc]+"."+ext)
