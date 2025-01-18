#!/bin/bash

set -e

source .redenv/bin/activate

PREFIX="${PREFIX:-!}"

[ -z "$OWNER" ] && echo "Set the OWNER!" && exit 1
[ -z "$TOKEN" ] && echo "Set the TOKEN!" && exit 1

if [ -z "$(ls -A data)" ]; then
  redbot-setup \
    --no-prompt \
    --instance-name RedBot \
    --data-path /home/red/data \
    --overwrite-existing-instance \
    --backend json
fi

redbot RedBot \
    --no-prompt \
    --token "${TOKEN}" \
    --owner "${OWNER}" \
    --prefix "${PREFIX}" \
    --mentionable