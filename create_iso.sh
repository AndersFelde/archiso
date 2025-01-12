#!/bin/bash

ISO_CONFIG_DIR=$(pwd)/archlive/airootfs/root/archinstall

sudo pacman -S --needed git archiso jq

mkdir -p archlive
cp -r /usr/share/archiso/configs/releng/* archlive
mkdir -p $ISO_CONFIG_DIR

cp install.py $ISO_CONFIG_DIR
cp post_install.sh $ISO_CONFIG_DIR
cp enable_secure_boot.sh $ISO_CONFIG_DIR
cp enable_tpm_autounlock.sh $ISO_CONFIG_DIR

git clone --depth=1 http://github.com/romkatv/powerlevel10k.git $ISO_CONFIG_DIR/powerlevel10k
git clone https://github.com/zsh-users/zsh-syntax-highlighting $ISO_CONFIG_DIR/zsh-syntax-highlighting
git clone https://github.com/zsh-users/zsh-autosuggestions $ISO_CONFIG_DIR/zsh-autosuggestions

git clone https://github.com/andersfelde/lvim $ISO_CONFIG_DIR/lvim
git clone https://github.com/andersfelde/qtile $ISO_CONFIG_DIR/qtile
git clone https://github.com/andersfelde/eww $ISO_CONFIG_DIR/eww
git clone https://github.com/andersfelde/rofi $ISO_CONFIG_DIR/rofi
git clone https://github.com/andersfelde/dotfiles $ISO_CONFIG_DIR/dotfiles

mkdir -p $ISO_CONFIG_DIR/packages
sudo pacman -Syw --noconfirm - < pacman_packages.txt --cachedir $ISO_CONFIG_DIR/packages/

mkdir -p aur_packages

while IFS= read -r package; do
    git clone https://aur.archlinux.org/$package.git aur_packages/$package
    cd aur_packages/$package
    makepkg -dc --skippgpcheck
    BUILD_PKG=$(find . -type f -name '*.pkg.tar.zst' ! -name '*-debug-*.pkg.tar.zst')
    cp $BUILD_PKG $ISO_CONFIG_DIR/packages/$package.pkg.tar.zst
    cd -
done < aur_packages.txt

sudo mkarchiso -v -r -w $(pwd)/archiso-tmp $(pwd)/archlive
