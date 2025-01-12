if [ "$EUID" -ne 0 ]; then 
    tput setaf 1
    echo "Must be run as root"
    tput sgr0

    exit
fi

printUpdate()
{
    tput setaf 2
    echo "$1"
    tput sgr0
}

if [ -z "$1" ]; then
    tput setaf 1
    echo "Username argument is required"
    tput sgr0

    exit 1
fi

username=$1
CONFIG_DIR="/opt/archinstall"

printUpdate "Updating pacman config"
sed -i '/Color/s/^#//g' /etc/pacman.conf
sudo sed -i '/^Color$/a ILoveCandy' /etc/pacman.conf
sed -i '/#ParallelDownloads/s/^#//' /etc/pacman.conf

printUpdate "Installing packages"
pacman --noconfirm -U $CONFIG_DIR/packages/*.pkg.tar.zst



printUpdate "Updating paru config"
sed -i '/BottomUp/s/^#//g' /etc/paru.conf
sed -i '/SudoLoop/s/^#//g' /etc/paru.conf
echo

# printUpdate "Setting up ly login manager"
# systemctl enable ly.service

systemctl enable --now touchegg
# for ly

printUpdate "Setting up zsh"
mv $CONFIG_DIR/powerlevel10k /usr/share/oh-my-zsh/custom/themes/powerlevel10k
mv $CONFIG_DIR/zsh-syntax-highlighting /usr/share/oh-my-zsh/custom/plugins/zsh-syntax-highlighting
mv $CONFIG_DIR/zsh-autosuggestions /usr/share/oh-my-zsh/custom/plugins/zsh-autosuggestions
chsh --shell /bin/zsh $username

printUpdate "Setting up config files"
sudo -i -u $username bash << EOF
cd ~
mv $CONFIG_DIR/dotfiles .dotfiles
cd .dotfiles
cp .dotter/desktop_example.toml .dotter/local.toml
dotter deploy -v --force
mv $CONFIG_DIR/rofi ~/.config/
mv $CONFIG_DIR/eww ~/.config/
mv $CONFIG_DIR/qtile ~/.config/
mv $CONFIG_DIR/lvim ~/.config/

mkdir -p ~/.local/share/lunarvim
ln -s /usr/share/lunarvim ~/.local/share/lunarvim/lvim
EOF


chmod +x /home/$username/.xinitrc
chmod +x /home/$username/.config/qtile/autostart.sh
chmod +x /home/$username/.config/qtile/scripts/*.sh
chmod +x /home/$username/.config/rofi/launchers/misc/*.sh

printUpdate "You are now done installing"