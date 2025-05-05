from subprocess import call


def touch(left: int, top: int):
    """
    Slow touch emulation

    left: x coordinate
    top: y coordinate
    """
    call(["adb", "shell", "input", "tap", str(left), str(top)])
