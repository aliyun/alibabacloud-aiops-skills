
# GRUB Boot-Stage Troubleshooting

This only covers GRUB2's boot.img and later stages; GRUB Legacy is not considered.

## Common GRUB Failure Types

### Missing Files Causing GRUB Runtime Failure

- **Missing kernel or initrd/initramfs**: This typically causes boot failure or an initramfs panic.
- **Missing files related to /boot/grub2/i386-pc**: Missing files will cause startup failure. It is recommended to reset the system disk or copy them from a machine of the same version.
- **Missing grub configuration file**:
  - **BIOS**: After `chroot /mnt`, run `grub2-install /dev/<SYSTEM_DISK>` to reinstall grub.
  - **UEFI**: After `chroot /mnt`, run `grub2-mkconfig -o /boot/efi/EFI/<OS_NAME>/grub.cfg` to regenerate the grub configuration.

### core.img Damage

Symptom: stuck at “Booting from Hard Disk...”. After `chroot /mnt`, run `grub2-install /dev/<SYSTEM_DISK>` to reinstall grub.

### The System /boot Directory Was Deleted

1. After `chroot /mnt`, reinstall grub2 with `grub2-install`.
2. After `chroot /mnt`, reinstall the kernel with the package manager.
3. After `chroot /mnt`, recreate the grub2 configuration file with `grub2-mkconfig`.
