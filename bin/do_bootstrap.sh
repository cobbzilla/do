#!/bin/bash

. ${HOME}/.digitalocean

if [ -z "${DO_ROOT_KEY}" ] ; then
  echo "No DO_ROOT_KEY found in environment. Usually it is in ${HOME}/.digitalocean"
  exit 1
fi

IP=${1}
if [ -z "${IP}" ] ; then
  echo "Usage $0 ip-address user /path/to/key.pub"
  exit 1
fi

USER=${2}
if [ -z "${USER}" ] ; then
  echo "Usage $0 ip-address user /path/to/key.pub"
  exit 1
fi

KEY_PATH=${3}
if [ -z "${KEY_PATH}" ] ; then
  echo "Usage $0 ip-address user /path/to/key.pub"
  exit 1
fi

IP=$($(dirname $0)/do droplet-ip ${IP})

ssh -i ${DO_ROOT_KEY} root@${IP} "bash -c '\
  useradd -m -s /bin/bash ${USER} && \
  adduser ${USER} sudo && \
  echo \"${USER} ALL=(ALL) NOPASSWD: ALL\" >> /etc/sudoers && \
  mkdir /home/${USER}/.ssh && \
  chown ${USER} /home/${USER}/.ssh && \
  chmod 700 /home/${USER}/.ssh \
'"

scp -i ${DO_ROOT_KEY} ${KEY_PATH} root@${IP}:/home/${USER}/.ssh/authorized_keys2

ssh -i ${DO_ROOT_KEY} root@${IP} "bash -c '\
  chown -R ${USER} /home/${USER}/.ssh && \
  chmod 700 /home/${USER}/.ssh/authorized_keys2 && \
  rm /root/.ssh/authorized_keys*
'"

mkdir -p ${HOME}/.digitalocean.d
PRIVATE_KEY=$(echo ${KEY_PATH} | sed -e 's/.pub$//')
echo "user: ${USER}
key_path: ${PRIVATE_KEY}
" > ${HOME}/.digitalocean.d/${IP}.yml
