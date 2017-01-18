#!/usr/bin/env python

REASON = {
    'OUTDIR': 1
}

class PlatformException(Exception):
    """
    When involve invalid platform, this exception will be raised.
    """
    def __init__(self, platform):
        self.platform = platform

    def __str__(self):
        return "Unknown or unsupported SDN controller platform: %s" % self.platform

class WorkspaceException(Exception):
    """
    When missing configure workspace or workspace is non-existed,
    this exception will be raised.
    """
    def __init__(self, workspace="", reason=None):
        self.workspace = workspace
        self.reason = reason

    def __str__(self):
        if self.workspace:
            if not self.reason:
                return "Workspace %s is non-existed or not a directory." % self.workspace
            elif REASON['OUTDIR'] == self.reason:
                return "'output' in workspace %s has been existing, but not a directory" % self.workspace
            else:
                return "Unknown reason exception occurred in workspace %s" % self.workspace
        else:
            return "Missing workspace. You need to set a experiment workspace directory to run the testcase."
