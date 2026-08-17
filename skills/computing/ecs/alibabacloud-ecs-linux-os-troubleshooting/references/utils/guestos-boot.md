
# Linux Boot-Stage Troubleshooting

This document describes troubleshooting for the first stage of VM OS boot, including BIOS/Legacy and UEFI.

## Boot Device Not Found

### no bootable device (BIOS booted but no boot device was found)

- **Check whether the MBR or system disk is damaged**: In the PE environment, run `fdisk -l`. If the system disk of the problematic instance is visible but `blkid` shows no corresponding partition, the system disk may be damaged. Read the first sector to confirm whether the MBR is damaged: `dd if=/dev/<SYSTEM_DISK> of=/tmp/mbr.txt bs=512 count=1`, `hexdump -C /tmp/mbr.txt`. For the MBR structure, see [Master boot record](https://zh.wikipedia.org/wiki/%E4%B8%BB%E5%BC%95%E5%AF%BC%E8%AE%B0%E5%BD%95).

## Boot Enters UEFI Shell (UEFI Boot Not Found)

- **Check whether the boot sector or image is damaged**: In the PE environment, run `fdisk -l`. If the system disk of the problematic instance is visible but `blkid` shows no corresponding partition, it may be damaged. Read the first two sectors and look for the PART signature (GPT). Check whether the files under `/boot/efi/EFI/` are complete. If all the preceding checks are normal, the issue is most likely with virtualized OVMF or block storage.

## Booting from hard disk...

- In the PE environment, run `fdisk -l` to check whether the disk format/label matches the boot requirements. (Fix example: if it was mistakenly changed to gpt, use gdisk to change it back to msdos, run `e2fsck` to synchronize the file system, reinstall grub2 in the chroot /mnt environment, and verify the root partition UUID.)
