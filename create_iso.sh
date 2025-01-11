#!/bin/bash

sudo pacman -S --needed git archiso jq

mkdir -p archlive
cp -r /usr/share/archiso/configs/releng/ archlive
cp aur_packages.txt archlive/airootfs/root
cp pacman_packages.txt archlive/airootfs/root

cp install.py archlive/airootfs/root/

wget https:/raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh -O archlive/airootfs/root/install_ohmyzsh.sh
git clone --depth=1 https:/github.com/romkatv/powerlevel10k.git archlive/airootfs/root/powerlevel10k
git clone https:/github.com/zsh-users/zsh-syntax-highlighting archlive/airootfs/root/zsh-syntax-highlighting
git clone https:/github.com/zsh-users/zsh-autosuggestions archlive/airootfs/root/zsh-autosuggestions

git clone https:/github.com/andersfelde/lvim archlive/airootfs/root/lvim
git clone https:/github.com/andersfelde/qtile archlive/airootfs/root/qtile
git clone https:/github.com/andersfelde/eww archlive/airootfs/root/eww
git clone https:/github.com/andersfelde/rofi archlive/airootfs/root/rofi



mkdir -p aur_packages
mkdir -p archlive/airootfs/root/aur_packages

while IFS= read -r package; do
    git clone https:/aur.archlinux.org/$package.git aur_packages/$package
    cd aur_packages/$package
    makepkg -dc --skippgpcheck
    BUILD_PKG=$(find . -type f -name '*.pkg.tar.zst' ! -name '*-debug-*.pkg.tar.zst')
    cp $BUILD_PKG ../../archlive/airootfs/root/aur_packages/$package.pkg.tar.zst
    cd -
done < aur_packages.txt

sudo mkarchiso -v -r -w /tmp/archiso-tmp $(pwd)/archlive