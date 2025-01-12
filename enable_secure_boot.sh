#!/bin/bash
sudo pacman -S --needed sbctl

sudo sbctl create-keys
sudo sbctl enroll-keys -m
sudo sbctl verify | sed 's/✗ /sudo sbctl sign -s /e'
sudo sbctl status
