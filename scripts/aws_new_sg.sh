#!/bin/sh
set -e
EC2="aws ec2 --region ${REGION:?required}"

$EC2 delete-security-group --group-name "${NAME:?required}" || true

SGID="$(
    $EC2 create-security-group \
        --group-name "${NAME:?required}" \
        --description "${NAME:?required}" \
    | jq -r '.GroupId'
)"

for spec in ${SPECS:?required}; do
    $EC2 authorize-security-group-ingress \
        --group-name "${NAME:?required}" \
        --protocol "${spec%/*}" \
        --port "${spec#*/}" \
        --cidr '0.0.0.0/0' 1>&2
done

echo "$SGID"
