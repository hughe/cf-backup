# Find some disks for backup.
#
# On the pi-top the external disks end up in /media/pi/DISK-LABEL if
# they are plugged in while the pi is running.  If they are plugged in
# before the pi starts they end up in /tmp/sda{1,2}.
#
# I could parse the output of `blkid` and `mount` to find the disk.
# Or `findmnt --json` looks really good.

import os
import logging
import stat

from typing import Optional, NamedTuple

logger = logging.getLogger(__name__)


class FindDisksResult(NamedTuple):
    backup_a: Optional[os.PathLike]
    backup_b: Optional[os.PathLike]
    cf_card: Optional[os.PathLike]



backup_disk_labels = set(["BACKUP_A", "BACKUP_B"])

def check_disk_type(disk_path_maybe: os.PathLike) -> Optional[tuple[str, os.PathLike]]:
    st = os.stat(disk_path_maybe)
    logger.debug("Checking: %s", disk_path_maybe)
    if stat.S_ISDIR(st.st_mode):
        try:
            backup_label_path = os.path.join(disk_path_maybe, "CF_BACKUP.LAB")
            logger.debug("Checking for: %s", backup_label_path)
            with open(backup_label_path, "r") as f:
                body = f.read() # Read the whole file.  It should be a single line.
                body = body.strip()

                if body in backup_disk_labels:
                    return (body, disk_path_maybe)
                else:
                    logging.error("File %s does not contain one of the expected labels", backup_label_path)
        except FileNotFoundError:
            pass

        dcim_path = os.path.join(disk_path_maybe, "DCIM")
        logger.debug("Checking for: %s", backup_label_path)
        try:
            dcim_st = os.stat(dcim_path)
            if stat.S_ISDIR(dcim_st.st_mode):
                return ("CF_CARD", disk_path_maybe)
        except FileNotFoundError:
            pass
            
            
    return None
    

def find_disks() -> FindDisksResult:
    backup_a = None
    backup_b = None
    cf_card = None
    
    prefix = os.path.abspath("/media/pi/")
    for fn in os.listdir(prefix):
        disk = check_disk_type(os.path.join(prefix, fn))
        if disk is not None:
            lab, mount_point = disk

            if lab == "BACKUP_A":
                if backup_a is not None:
                    logger.error("Found two disks labelled BACKUP_A")
                    return None
                backup_a = mount_point
            elif lab == "BACKUP_B":
                if backup_b is not None:
                    logger.error("Found two disks labelled BACKUP_B")
                    return None
                backup_b = mount_point
            elif lab == "CF_CARD":
                if cf_card is not None:
                    logger.error("Found two disks labelled CF_CARD")
                    return None
                cf_card = mount_point
                
    return FindDisksResult(backup_a, backup_b, cf_card)

if __name__ == '__main__':
    import sys
    
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stderr)
    root.addHandler(handler)

    res = find_disks()
    if res is None:
        print("No disks found")
    else:
        print(repr(res))
                
            
            
            
        
        
                
                
                        
                
        
        





