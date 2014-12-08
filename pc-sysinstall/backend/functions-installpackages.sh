#!/bin/sh
#-
# Copyright (c) 2010 iXsystems, Inc.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# $FreeBSD: head/usr.sbin/pc-sysinstall/backend/functions-installpackages.sh 247734 2013-03-03 23:01:46Z jpaetzel $

# Functions which check and load any optional packages specified in the config

. ${BACKEND}/functions.sh
. ${BACKEND}/functions-parse.sh

# Check for any packages specified, and begin loading them
install_packages()
{
  echo "Installing packages..."
  sleep 3
  HERE=`pwd`
  rc_halt "install -dm0755 ${FSMNT}/var/cache/pacman/pkg"
  rc_halt "install -dm0755 ${FSMNT}/var/lib/pacman"

  # Update the repo database
  echo "Updating pacman database"
  pacman -r ${FSMNT} -Sy --cachedir="${FSMNT}/var/cache/pacman/pkg"
	
  # Lets start by cleaning up the string and getting it ready to parse
  pacman -r ${FSMNT} -S ${INIT} base --noconfirm --cachedir="${FSMNT}/var/cache/pacman/pkg"
  echo_log "Package installation complete!"
  
  if [ "${BOOTMANAGER}" == "grub" ];then
	echo "Installing grub"
	pacman -r ${FSMNT} -S grub --noconfirm --cachedir="${FSMNT}/var/cache/pacman/pkg"
  fi

  rc_halt "cd ${HERE}"
};
