import importlib
import subprocess
from pathlib import Path

import archinstall
from archinstall.default_profiles.xorg import XorgProfile
from archinstall.lib import disk, models
from archinstall.lib.disk.device_model import DiskLayoutConfiguration
from archinstall.lib.interactions import (select_devices,
                                          suggest_single_disk_layout)
from archinstall.lib.models import User
from archinstall.lib.profile import ProfileConfiguration
from archinstall.lib.utils.util import get_password
# from archinstall.scripts.guided import perform_installation
from archinstall.tui import Alignment, EditMenu, Tui

SUDO_USER = None

def ask_user(title="", default_text="") -> str:
    return (
        EditMenu(
            title=title,
            allow_skip=False,
            alignment=Alignment.CENTER,
            default_text=default_text,
        )
        .input()
        .text()
    )


def prompt_disk_layout(fs_type="ext4", separate_home=False) -> None:
    fs_type = disk.FilesystemType(fs_type)

    devices = select_devices()
    modifications = suggest_single_disk_layout(
        devices[0], filesystem_type=fs_type, separate_home=separate_home
    )

    archinstall.arguments["disk_config"] = disk.DiskLayoutConfiguration(
        config_type=disk.DiskLayoutType.Default, device_modifications=[modifications]
    )


def parse_disk_encryption() -> None:
    modification: DiskLayoutConfiguration = archinstall.arguments["disk_config"]
    partitions: list[disk.PartitionModification] = []

    # encrypt all partitions except the /boot
    for mod in modification.device_modifications:
        partitions += list(
            filter(lambda x: x.mountpoint != Path("/boot"), mod.partitions)
        )

    archinstall.arguments["disk_encryption"] = disk.DiskEncryption(
        encryption_type=disk.EncryptionType.Luks,
        encryption_password=get_password("Enter disk encryption password: "),
        partitions=partitions,
    )


def parse_user():
    SUDO_USER = ask_user("Sudo user username", "kippster")
    password = get_password(text="Sudo user password")
    return [User(SUDO_USER, password, sudo=True)]


def chroot_cmd(cmd, user="root"):
    installation_mount_point = "/mnt/archiso"
    subprocess.run(
        ["arch-chroot", "-u", "root", installation_mount_point, "/bin/bash", "-c", cmd]
    )


def install():
    archinstall.arguments["uki"] = True
    archinstall.arguments["profile_config"] = ProfileConfiguration(XorgProfile())
    archinstall.arguments["audio_config"] = models.AudioConfiguration(
        audio=models.Audio.Pipewire
    )
    archinstall.arguments["network_config"] = models.NetworkConfiguration(
        models.NicType.NM
    )
    archinstall.arguments["boot_loader"] = models.Bootloader.Systemd
    archinstall.arguments["hostname"] = "minimal-arch"
    archinstall.arguments["packages"] = []
    with Tui():
        prompt_disk_layout()
        parse_disk_encryption()
        archinstall.arguments["!users"] = parse_user()
        archinstall.arguments["!root-password"] = get_password("Enter root password")
        archinstall.arguments["hostname"] = ask_user("Enter hostname", "arch")
    importlib.import_module("archinstall.scripts.guided")


def install_packages():
    with open("pacman_packages.txt") as f:
        pacman_packages = f.read().splitlines()

    chroot_cmd(f"pacman -Syu {' '.join(pacman_packages)}")

    with open("aur_packages.txt") as f:
        aur_packages = f.read().splitlines()

    chroot_cmd(f"pacman -U {'pkg.tar.zst '.join(aur_packages)}")


def configure_system():
    chroot_cmd(
        "sed -i '/BottomUp/s/^#//g' /etc/paru.conf; sed -i '/SudoLoop/s/^#//g' /etc/paru.conf"
    )
    chroot_cmd("chmod o+x /root/install_ohmyzsh.sh")
    chroot_cmd("/root/install_ohmyzsh.sh", user=SUDO_USER)

    chroot_cmd(f"mv /root/powerlevel10k /home/{SUDO_USER}/.oh-my-zsh/custom/themes/")
    chroot_cmd(f"mv /root/zsh-syntax-highlighting /home/{SUDO_USER}/.oh-my-zsh/custom/plugins/")
    chroot_cmd(f"mv /root/zsh-autosuggestions /home/{SUDO_USER}/.oh-my-zsh/custom/plugins/")
    chroot_cmd(f"chown -R {SUDO_USER}:{SUDO_USER} /home/{SUDO_USER}/.oh-my-zsh")
    chroot_cmd(f"chsh -s /bin/zsh {SUDO_USER}")
    chroot_cmd(f"mv /root/dotfiles /home/{SUDO_USER}/.dotfiles")
    chroot_cmd(f"cp /home/{SUDO_USER}/.dotfiles/.dotter/desktop_example.toml /home/{SUDO_USER}/.dotfiles/.dotter/local.toml")
    chroot_cmd(f"chown -R {SUDO_USER}:{SUDO_USER} /home/{SUDO_USER}/.dotfiles")
    chroot_cmd(f"cd /home/{SUDO_USER}/.dotfiles && dotter deploy --force -v", user=SUDO_USER)
    chroot_cmd(f"mv /root/rofi /home/{SUDO_USER}/.config/")
    chroot_cmd(f"mv /root/eww /home/{SUDO_USER}/.config/")
    chroot_cmd(f"mv /root/lvim /home/{SUDO_USER}/.config/")
    chroot_cmd(f"mv /root/qtile /home/{SUDO_USER}/.config/")




if __name__ == "__main__":
    install()
    install_packages()
