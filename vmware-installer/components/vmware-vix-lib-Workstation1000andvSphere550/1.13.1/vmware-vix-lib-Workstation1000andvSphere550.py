"""
Copyright 2007 VMware, Inc.  All rights reserved. -- VMware Confidential

VIX Workstation1000andvSphere550 library component installer.
"""
DEST = LIBDIR/'vmware-vix'

class VIXLibWorkstation1000andvSphere550(Installer):
   def InitializeInstall(self, old, new, upgrade):
      self.AddTarget('File', 'lib/*', DEST)
