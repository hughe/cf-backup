#!/bin/bash

sudo cp *.py project.cfg /home/pi/Desktop/Projects/cf-backup/ && \
    sudo chown pi.pi /home/pi/Desktop/Projects/cf-backup/* && \
    cd /home/pi/Desktop/Projects/cf-backup/ && \
    sudo -u pi python3 cf_backup.py
