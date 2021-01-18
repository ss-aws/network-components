# network-infrastructure
# Description
This project creates a VPC, Public Subnet, Private Subnet, Ec2 , Security Groups, Network Interface,IGW, LoadBalancer, AutoScalingGroup, Route53
# prerequisites
Python installed
Pip installed
troposphere installed
aws cli installed
Editor example - Atom, VS Code
aws acces key
aws acces token

# deploy template
AWS Cli

#install troposphere
pip install troposphere

# install awscli
pip install awscli

# command to deploy template

aws cloudformation deploy --template-file /network-infrastructure/network-topology/templates/network-components-template.yaml --stack-name "NetworkStack"

#  EC2 Instances

There are 2 solutions to the given problem statement

option 1. Deploy the template network-components-ec2-userdata-template.yaml using aws cli.The EC2 Instance has a LaunchConfiguration with userdata to host the static page
option 2. Deploy the template network-components-ec2-template.yaml using aws cli. Launch using aws cli and after it's launched run the shell scripts

# descriptor

The IAC tool will read this json file from cloudformation.json
