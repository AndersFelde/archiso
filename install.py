# import importlib
import shutil
import subprocess
from pathlib import Path

import archinstall
from archinstall import SysInfo, debug, info
from archinstall.default_profiles.profile import GreeterType
from archinstall.default_profiles.xorg import XorgProfile
from archinstall.lib import disk, locale, models
from archinstall.lib.configuration import ConfigurationOutput
from archinstall.lib.disk.device_model import DiskLayoutConfiguration
from archinstall.lib.global_menu import GlobalMenu
from archinstall.lib.hardware import GfxDriver
from archinstall.lib.installer import Installer
from archinstall.lib.interactions import (select_devices,
                                          suggest_single_disk_layout)
from archinstall.lib.interactions.general_conf import ask_chroot
from archinstall.lib.models import AudioConfiguration, Bootloader, User
from archinstall.lib.models.network_configuration import NetworkConfiguration
from archinstall.lib.profile import ProfileConfiguration
from archinstall.lib.profile.profiles_handler import profile_handler
from archinstall.lib.utils.util import get_password
# from archinstall.scripts.guided import perform_installation
from archinstall.tui import Alignment, EditMenu, Tui

SUDO_USER = None
CONFIG_DIR = "/opt/archinstall"
ISO_CONFIG_DIR = "/root/archinstall"
MOUNT_POINT: str | Path = ""


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
    global SUDO_USER
    SUDO_USER = ask_user("Sudo user username", "kippster")
    password = get_password(text="Sudo user password")
    return [User(SUDO_USER, password, sudo=True)]


def chroot_cmd(cmd,user="root"):
    ret = subprocess.run(["arch-chroot", "-u", "root", MOUNT_POINT, "/bin/bash", "-c", cmd])
    if ret.returncode != 0:
        raise Exception(f"Failed to run command: {cmd}")


def cmd(cmd):
    subprocess.run(cmd, shell=True)


def mv(source, destination):
    shutil.move(source, destination)

def configure_system():
    info("Copying configuration files")
    mv(ISO_CONFIG_DIR, f"{MOUNT_POINT}{CONFIG_DIR}")
    # info("Installing custom packages")
    # installation.arch_chroot(
    #     f"/bin/bash -c 'pacman -U {CONFIG_DIR}/packages/*.pkg.tar.zst --noconfirm'"
    # )
    chroot_cmd(f"chown -R {SUDO_USER}:{SUDO_USER} {CONFIG_DIR}")
    chroot_cmd(f"chmod +x {CONFIG_DIR}/post_install.sh")
    info("Starting post install script")
    chroot_cmd(f"{CONFIG_DIR}/post_install.sh {SUDO_USER}")

    # installation.arch_chroot(f"mkdir {CONFIG_DIR}")
    # mv(f"{ISO_CONFIG_DIR}/packages", f"{installation.target}{CONFIG_DIR}")


# def configure_system(installation: Installer):

#     _config_dir = f"{installation.target}{CONFIG_DIR}"
#     mv(ISO_CONFIG_DIR, _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/post_install.sh", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/install_ohmyzsh.sh", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/powerlevel10k", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/zsh-syntax-highlighting", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/zsh-autosuggestions", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/rofi", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/eww", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/lvim", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/qtile", _config_dir)
#     mv(f"{ISO_CONFIG_DIR}/dotfiles", _config_dir)
#     installation.arch_chroot(f"chown -R {SUDO_USER}:{SUDO_USER} {CONFIG_DIR}")
#     installation.arch_chroot(f"chmod +x {CONFIG_DIR}/post_install.sh")
#     installation.arch_chroot(f"{CONFIG_DIR}/post_install.sh {SUDO_USER}")


def perform_installation(mountpoint: Path) -> None:
    """
    Performs the installation steps on a block device.
    Only requirement is that the block devices are
    formatted and setup prior to entering this function.
    """
    info("Starting installation...")
    disk_config: disk.DiskLayoutConfiguration = archinstall.arguments["disk_config"]

    # Retrieve list of additional repositories and set boolean values appropriately
    enable_testing = "testing" in archinstall.arguments.get(
        "additional-repositories", []
    )
    enable_multilib = "multilib" in archinstall.arguments.get(
        "additional-repositories", []
    )
    run_mkinitcpio = not archinstall.arguments.get("uki")
    locale_config: locale.LocaleConfiguration = archinstall.arguments["locale_config"]
    disk_encryption: disk.DiskEncryption = archinstall.arguments.get(
        "disk_encryption", None
    )

    with Installer(
        mountpoint,
        disk_config,
        disk_encryption=disk_encryption,
        kernels=archinstall.arguments.get("kernels", ["linux"]),
    ) as installation:
        # Mount all the drives to the desired mountpoint
        if disk_config.config_type != disk.DiskLayoutType.Pre_mount:
            installation.mount_ordered_layout()

        installation.sanity_check()

        if disk_config.config_type != disk.DiskLayoutType.Pre_mount:
            if (
                disk_encryption
                and disk_encryption.encryption_type != disk.EncryptionType.NoEncryption
            ):
                # generate encryption key files for the mounted luks devices
                installation.generate_key_files()

        if mirror_config := archinstall.arguments.get("mirror_config", None):
            installation.set_mirrors(mirror_config, on_target=False)

        installation.minimal_installation(
            testing=enable_testing,
            multilib=enable_multilib,
            mkinitcpio=run_mkinitcpio,
            hostname=archinstall.arguments.get("hostname"),
            locale_config=locale_config,
        )

        if mirror_config := archinstall.arguments.get("mirror_config", None):
            installation.set_mirrors(mirror_config, on_target=True)

        if archinstall.arguments.get("swap"):
            installation.setup_swap("zram")

        if (
            archinstall.arguments.get("bootloader") == Bootloader.Grub
            and SysInfo.has_uefi()
        ):
            installation.add_additional_packages("grub")

        installation.add_bootloader(
            archinstall.arguments["bootloader"], archinstall.arguments.get("uki", False)
        )

        # If user selected to copy the current ISO network configuration
        # Perform a copy of the config
        network_config: NetworkConfiguration | None = archinstall.arguments.get(
            "network_config", None
        )

        if network_config:
            network_config.install_network_config(
                installation, archinstall.arguments.get("profile_config", None)
            )

        if users := archinstall.arguments.get("!users", None):
            installation.create_users(users)

        audio_config: AudioConfiguration | None = archinstall.arguments.get(
            "audio_config", None
        )
        if audio_config:
            audio_config.install_audio_config(installation)
        else:
            info("No audio server will be installed")

        if (
            archinstall.arguments.get("packages", None)
            and archinstall.arguments.get("packages", None)[0] != ""
        ):
            installation.add_additional_packages(
                archinstall.arguments.get("packages", None)
            )

        if profile_config := archinstall.arguments.get("profile_config", None):
            profile_handler.install_profile_config(installation, profile_config)

        if timezone := archinstall.arguments.get("timezone", None):
            installation.set_timezone(timezone)

        if archinstall.arguments.get("ntp", False):
            installation.activate_time_synchronization()

        if archinstall.accessibility_tools_in_use():
            installation.enable_espeakup()

        if (root_pw := archinstall.arguments.get("!root-password", None)) and len(
            root_pw
        ):
            installation.user_set_pw("root", root_pw)

        if profile_config := archinstall.arguments.get("profile_config", None):
            profile_config.profile.post_install(installation)

        # If the user provided a list of services to be enabled, pass the list to the enable_service function.
        # Note that while it's called enable_service, it can actually take a list of services and iterate it.
        if archinstall.arguments.get("services", None):
            installation.enable_service(archinstall.arguments.get("services", []))

        # If the user provided custom commands to be run post-installation, execute them now.
        if archinstall.arguments.get("custom-commands", None):
            archinstall.run_custom_user_commands(
                archinstall.arguments["custom-commands"], installation
            )

        installation.genfstab()

        configure_system()

        if not archinstall.arguments.get("silent"):
            with Tui():
                chroot = ask_chroot()

            if chroot:
                try:
                    installation.drop_to_shell()
                except Exception:
                    pass

        info(
            "For post-installation tips, see https://wiki.archlinux.org/index.php/Installation_guide#Post-installation"
        )

    debug(f"Disk states after installing:\n{disk.disk_layouts()}")


def install():
    archinstall.arguments["uki"] = True
    archinstall.arguments["profile_config"] = ProfileConfiguration(
        XorgProfile(), GfxDriver.AllOpenSource, GreeterType.Ly
    )
    archinstall.arguments["audio_config"] = models.AudioConfiguration(
        audio=models.Audio.Pipewire
    )
    archinstall.arguments["network_config"] = models.NetworkConfiguration(
        models.NicType.NM
    )
    archinstall.arguments["boot_loader"] = models.Bootloader.Systemd
    archinstall.arguments["timezone"] = "Europe/Oslo"
    with Tui():
        prompt_disk_layout()
        parse_disk_encryption()
        archinstall.arguments["!users"] = parse_user()
        archinstall.arguments["!root-password"] = get_password("Enter root password")
        archinstall.arguments["hostname"] = ask_user("Enter hostname", "arch")
        global_menu = GlobalMenu(data_store=archinstall.arguments)
        global_menu.set_enabled("parallel downloads", True)
        global_menu.run()

    config = ConfigurationOutput(archinstall.arguments)
    config.write_debug()
    config.save()

    if archinstall.arguments.get("dry_run"):
        exit(0)

    if not archinstall.arguments.get("silent"):
        with Tui():
            if not config.confirm_config():
                debug("Installation aborted")
                return install()

    fs_handler = disk.FilesystemHandler(
        archinstall.arguments["disk_config"],
        archinstall.arguments.get("disk_encryption", None),
    )

    fs_handler.perform_filesystem_operations()
    global MOUNT_POINT
    MOUNT_POINT = archinstall.arguments.get("installation.target", Path("/mnt"))
    perform_installation(MOUNT_POINT)
    info("Installation complete. You can now reboot.")


if __name__ == "__main__":
    install()
    # install_packages()
    # configure_system()
