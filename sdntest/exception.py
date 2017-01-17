#!/usr/bin/env python2

class PlatformException(Exception):
    """
    """
    def __init__(self, platform):
        self.platform = platform

    def __str__(self):
        return "Unknown or unsupported SDN controller platform: %s" % self.platform
