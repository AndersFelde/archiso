echo "Warning! Secure boot must be activated before continuing"
sleep 2
read -p "Enter the path to the encrypted partition (e.g /dev/nvme0n1p2)" partition_path
clevis luks bind -d $partition_path tpm2 '{}'