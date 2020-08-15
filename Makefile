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
ssh: state/ec2_ip state/minecraft.pem
	${SSH}

.PHONY: stop
stop: # state/ec2_ip state/minecraft.pem
	${SSH} sudo systemctl stop minecraft-server

.PHONY: export
export: stop | worlds # state/ec2_ip
ifeq (${NO_BACKUP},true)
	scp -i state/minecraft.pem "core@$$(cat state/ec2_ip):/tmp/minecraft_world.tar.gz" "worlds/minecraft_world_$$(date +%11s).tar.gz"
endif

.PHONY: save
save: export # state/ec2_ip state/minecraft.pem
	${SSH} sudo systemctl start minecraft-server

.PHONY: delete-key
delete-key: export # state/ec2_keypair_name state/minecraft.pem state/minecraft.pem.pub
	${EC2} delete-key-pair --key-name "$$(cat state/ec2_keypair_name)"
	rm state/ec2_keypair_name state/minecraft.pem state/minecraft.pem.pub

.PHONY: kill
kill: delete-key # state/ec2_instance state/ec2_ip state/ec2_keypair_name
	${EC2} terminate-instances --instance-ids "$$(cat state/ec2_instance)"
	rm state/ec2_instance state/ec2_ip

.PHONY: list
list:
	${EC2} describe-network-interfaces | jq -r '.NetworkInterfaces[] | .Association.PublicIp'

# ,--------------,
# | file targets |
# '--------------'

worlds:
	mkdir worlds

state:
	mkdir state

state/minecraft.pem: | state
	ssh-keygen -t rsa -b 2048 -f "$@"

state/ec2_keypair_name: state/minecraft.pem # state/minecraft.pem.pub
	date '+minecraft_%11s' > "$@"
	${EC2} import-key-pair --key-name "$$(cat "$@")" --public-key-material "fileb://$<.pub"

.INTERMEDIATE: state/mc.json
state/mc.json: mc.yaml | state
	docker run -i --rm quay.io/coreos/fcct:release --pretty --strict < "$<" > "$@"

state/ec2_instance: state/mc.json state/ec2_keypair_name
	${EC2} describe-security-groups \
	| jq -e 'any(.SecurityGroups[]; select(.GroupName == "minecraft"))' \
		|| REGION="${REGION}" SPECS="${OPEN_PORTS}" NAME=minecraft scripts/aws_new_sg.sh
	${EC2} run-instances \
		--image-id "${AMI}" \
		--instance-type ${INSTANCE_TYPE} \
		--key-name "$$(cat state/ec2_keypair_name)" \
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

state/ec2_host: state/ec2_ip state/ec2_keypair_name
	printf 'Host %s\n\tUser core\n\tHostName %s\n\tIdentityFile ~/Minecraft/keys/%s\n' "$(cat state/ec2_keypair_name)" "$(cat state/ec2_ip)" "$(cat state/ec2_keypair_name)" > "$@"
