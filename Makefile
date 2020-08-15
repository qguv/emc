# requirements: jq, aws, openssh-client, bash (sorry, need pipefail)

REGION		?= eu-central-1
INSTANCE_TYPE	?= t3.xlarge
AMI		?= ami-0ffc658f54d9b6332
OPEN_PORTS	?= tcp/22 tcp/25565 udp/25565

SHELL=/bin/bash -eo pipefail
EC2=aws ec2 --region "${REGION}"
SSH=ssh -i state/minecraft.pem "core@$$(cat state/ec2_ip)"

# ,---------------------,
# | convenience targets |
# '---------------------'

.PHONY: info
info: state/ec2_ip
	@cat "$<"

.PHONY: ssh
ssh: state/ec2_ip
	${SSH}

.PHONY: export
export: | worlds # state/ec2_ip
	${SSH} sudo systemctl stop minecraft-server
	scp -i state/minecraft.pem "core@$$(cat state/ec2_ip):/tmp/minecraft_world.tar.gz" "worlds/minecraft_world_$$(date +%11s).tar.gz"

.PHONY: save
save: export # state/ec2_ip state/minecraft.pem
	${SSH} sudo systemctl start minecraft-server


.PHONY: kill
kill: export # state/ec2_instance state/ec2_ip state/keypair_name
	${EC2} terminate-instances --instance-ids "$$(cat state/ec2_instance)"
	rm state/ec2_instance state/ec2_ip
	${EC2} delete-key-pair --key-name "$$(cat state/keypair_name)"
	rm state/keypair_name state/minecraft.pem

.PHONY: kill9
kill9: # state/ec2_instance state/ec2_ip
	${EC2} terminate-instances --instance-ids "$$(cat state/ec2_instance)"
	rm state/ec2_instance state/ec2_ip

# ,--------------,
# | file targets |
# '--------------'

worlds:
	mkdir worlds

state:
	mkdir state

state/minecraft.pem: | state
	ssh-keygen -t rsa -b 2048 -f "$@"

state/keypair_name: state/minecraft.pem
	date '+minecraft_%11s' > "$@"
	${EC2} import-key-pair --key-name "$$(cat "$@")" --public-key-material "$$(cat "$<.pub")"

state/mc.json: mc.yaml | state
	docker run -i --rm quay.io/coreos/fcct:release --pretty --strict < "$<" > "$@"

state/ec2_instance: state/mc.json state/keypair_name
	${EC2} describe-security-groups \
	| jq -e 'any(.SecurityGroups[]; select(.GroupName == "minecraft"))' \
		|| REGION="${REGION}" SPECS="${OPEN_PORTS}" NAME=minecraft scripts/aws_new_sg.sh
	${EC2} run-instances \
		--image-id "${AMI}" \
		--instance-type ${INSTANCE_TYPE} \
		--key-name "$$(cat state/keypair_name)" \
		--user-data "file://$<" \
		--security-groups minecraft \
	| jq -re '.Instances[0].InstanceId' > "$@"

state/ec2_ip: state/ec2_instance
	until \
		${EC2} describe-network-interfaces --filter Name=attachment.instance-id,Values="$$(cat "$<")" \
		| jq -re '.NetworkInterfaces[0].Association.PublicIp' > "$@"; \
	do \
		sleep 1; \
	done
