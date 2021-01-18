#!/usr/bin/env python

from troposphere import Base64, FindInMap, GetAtt, Join, Output, Export, Sub, GetAZs
from troposphere import Parameter, Condition, Ref, Template, Equals, Not, If, Or, Select
import troposphere.ec2 as ec2
import troposphere.cloudwatch as cloudwatch
import troposphere.cloudformation as cloudformation
import troposphere.cloudtrail as cloudtrail
import troposphere.ec2 as ec2
from troposphere.ec2 import SecurityGroup
import troposphere.elasticloadbalancing as elb
import troposphere.route53 as route53
import troposphere.autoscaling as autoscaling
import troposphere.policies as policies
import sys, os, argparse, json
from customcomponents import CustomRoute53ZoneInfo

class NetworkingTemplate:

	def __init__(self):
		self.template = Template()

	def setOutput(self, key, value):
		self.template.add_output(Output(
			key,
			Value=value
	))

	def addParams(self):
		self.vpc_cidr_range = self.template.add_parameter(Parameter(
			"VpcCidrRange",
			Description = "Cidr range for VPC",
			Type = "String",
			MinLength = 9,
			MaxLength = 18,
			AllowedPattern = "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
			ConstraintDescription = "must be a valid IP CIDR range of the form x.x.x.x/x."
		))

		self.priv_subnet_cidrs = self.template.add_parameter(Parameter(
			"PrivCidrRanges",
			Description = "list of private subnet ranges",
			Type = "CommaDelimitedList"
		))

		self.pub_subnet_cidrs = self.template.add_parameter(Parameter(
			"PubCidrRanges",
			Description = "list of public subnet ranges",
			Type = "CommaDelimitedList"
		))

		self.az = self.template.add_parameter(Parameter(
    				"AvailabilityZone",
    				Type="String"
		))

		self.security_group_id = self.template.add_parameter(Parameter(
					"SecurityGroup",
					Type="CommaDelimitedList"
		))

		self.key_name_param = self.template.add_parameter(Parameter(
					"SSHKey",
					Type="CommaDelimitedList",
					Default="Shweta"
		))

		self.instance_type = self.template.add_parameter(Parameter(
					"Instance",
					Type="String",
					Description="WebServer EC2 instance type",
					Default="m1.small",
					AllowedValues=[
            						"t1.micro", "m1.small", "m1.medium", "m1.large", "m1.xlarge"
            		],
					ConstraintDescription="must be a valid EC2 instance type."
		))

		self.load_balancer_port = self.template.add_parameter(Parameter(
			"WebServerPort",
			Type = "String",
			Default = "443",
			Description="TCP/IP port of the web server"
		))

		self.template.add_mapping('AzMap', {
		    "us-east-1a": {"AMI": "ami-dd48a1ac"},
		    "us-east-1b": {"AMI": "ami-eb4ca59a"},
		    "us-east-1c": {"AMI": "ami-dc48a1ad"}
		})

	def addResources(self):

		name = "MyVpc"
		my_vpc = self.template.add_resource(ec2.VPC(
			name,
			CidrBlock = Ref(self.vpc_cidr_range),
			EnableDnsSupport = True,
			EnableDnsHostnames = True,
			InstanceTenancy = "default"
		))

		###########
		# subnets #
		###########
	    # priv subnet #1
		name = "PrivSubnetA"
		priv_subnet_a = self.template.add_resource(ec2.Subnet(
			name,
			VpcId = Ref(my_vpc),
			CidrBlock = Select(0, Ref(self.priv_subnet_cidrs)),
			AvailabilityZone = Join("", [ Ref("AWS::Region"), "a" ] )
		))
		# priv subnet #2
		name = "PrivSubnetB"
		priv_subnet_b = self.template.add_resource(ec2.Subnet(
			name,
			VpcId = Ref(my_vpc),
			CidrBlock = Select(1, Ref(self.priv_subnet_cidrs)),
			AvailabilityZone = Join("", [ Ref("AWS::Region"), "b" ] )
		))

		## pub
		# pub subnet #1
		name = "PubSubnetA"
		pub_subnet_a = self.template.add_resource(ec2.Subnet(
			name,
			VpcId = Ref(my_vpc),
			CidrBlock = Select(0, Ref(self.pub_subnet_cidrs)),
			AvailabilityZone = Join("", [ Ref("AWS::Region"), "a" ] )
		))
		# pub subnet #2
		name = "PubSubnetB"
		pub_subnet_b = self.template.add_resource(ec2.Subnet(
			name,
			VpcId = Ref(my_vpc),
			CidrBlock = Select(1, Ref(self.pub_subnet_cidrs)),
			AvailabilityZone = Join("", [ Ref("AWS::Region"), "b" ] )
		))
		################
		# route tables #
		################
		# public
		public_route_table_name = "PublicRouteTable"
		public_route_table = self.template.add_resource(ec2.RouteTable(
			public_route_table_name,
			VpcId = Ref(my_vpc)
		))
		public_route_table_associationA = self.template.add_resource(ec2.SubnetRouteTableAssociation(
			"PublicRTAssociationA",
			RouteTableId = Ref(public_route_table),
			SubnetId = Ref(pub_subnet_a)
		))
		public_route_table_associationB = self.template.add_resource(ec2.SubnetRouteTableAssociation(
			"PublicRTAssociationB",
			RouteTableId = Ref(public_route_table),
			SubnetId = Ref(pub_subnet_b)
		))
		# private
		private_route_table_name_a = "PrivateRouteTableA"
		private_route_table_a = self.template.add_resource(ec2.RouteTable(
			private_route_table_name_a,
			VpcId = Ref(my_vpc)
		))

		private_route_table_name_b = "PrivateRouteTableB"
		private_route_table_b = self.template.add_resource(ec2.RouteTable(
			private_route_table_name_b,
			VpcId = Ref(my_vpc)
		))

		private_route_table_associationA = self.template.add_resource(ec2.SubnetRouteTableAssociation(
			"PrivateRTAssociationA",
			RouteTableId = Ref(private_route_table_a),
			SubnetId = Ref(priv_subnet_a)
		))
		private_route_table_associationB = self.template.add_resource(ec2.SubnetRouteTableAssociation(
			"PrivateRTAssociationB",
			RouteTableId = Ref(private_route_table_b),
			SubnetId = Ref(priv_subnet_b)
		))

		# igw
		igw_name = "myigw"
		igw = self.template.add_resource(ec2.InternetGateway(
			igw_name
		))

		vpc_attach = self.template.add_resource(ec2.VPCGatewayAttachment(
			"myIGWAttachVPC",
			VpcId = Ref(my_vpc),
			InternetGatewayId = Ref(igw)
		))


		###  Logging ###
		my_vpc_flow_logs = self.template.add_resource(ec2.FlowLog(
			"MyVpcFlowLogs",
			DeliverLogsPermissionArn = Join("", [ "arn:aws:iam::", Ref("AWS::AccountId"), ":role/AWS_FLOW_LOGS" ]),
			LogGroupName = Join("", [ "VpcFlowLogsLogGroup", "-", "MyVPC" ]),
			ResourceId = Ref(my_vpc),
			ResourceType = "VPC",
			TrafficType = "ALL"
		))
		#private instance security group
		my_ec2_security_group = ec2.SecurityGroup(
				"MySecurityGroup",
				GroupDescription = "Security Group",
				SecurityGroupIngress=[
					   ec2.SecurityGroupRule(
					   IpProtocol='tcp',
					   FromPort='443',
					   ToPort='443',
					   CidrIp=Ref(self.security_group_id)
					  )
				],
				SecurityGroupEgress =[
						ec2.SecurityGroupRule(
						IpProtocol='tcp',
						FromPort='443',
						ToPort='443',
						CidrIp='10.0.0.0/20'
						)
				],
				VpcId = Ref(my_vpc)
		)

		# Web Server Instances
		web_server_instances = []
		instance_priv_sub_a = self.template.add_resource(ec2.Instance(
	            "Ec2InstancePrivateSubnetA",
	            SecurityGroups=[Ref(my_ec2_security_group)],
	            KeyName=Ref(self.key_name_param),
	            InstanceType=Ref("InstanceType"),
				SubnetId = GetAtt(priv_subnet_a, "SubnetId"),
	            ImageId=FindInMap("AzMap", Ref("AWS::Region"), "AMI")
		))
		instance_priv_sub_b = self.template.add_resource(ec2.Instance(
	            "Ec2InstancePrivateSubnetB",
	            SecurityGroups=[Ref(my_ec2_security_group)],
	            KeyName=Ref(self.key_name_param),
	            InstanceType=Ref("InstanceType"),
				SubnetId = GetAtt(priv_subnet_b, "SubnetId"),
	            ImageId=FindInMap("AzMap", Ref("AWS::Region"), "AMI")
	       ))

		web_server_instances.append(instance_priv_sub_a)
		web_server_instances.append(instance_priv_sub_b)

		#instance eni
		my_private_eni_a = self.template.add_resource(ec2.NetworkInterface(
			"MyPrivateEniA",
			SourceDestCheck = "false",
			SubnetId = GetAtt(priv_subnet_a, "SubnetId"),
			GroupSet = [ Ref(my_ec2_security_group) ]
		))

		#network interface attachment
		my_ec2_network_attachment_a = self.template.add_resource(ec2.NetworkInterfaceAttachment(
			"MyPrivateEniAttachmentA",
			DeviceIndex = "1",
			InstanceId = Ref(instance_priv_sub_a),
			NetworkInterfaceId = Ref(my_private_eni_a)
		))

		#instance eni
		my_private_eni_b = self.template.add_resource(ec2.NetworkInterface(
			"MyPrivateEniB",
			SourceDestCheck = "false",
			SubnetId = GetAtt(priv_subnet_b, "SubnetId"),
			GroupSet = [ Ref(my_ec2_security_group) ]
		))

		#network interface attachment
		my_ec2_network_attachment_b = self.template.add_resource(ec2.NetworkInterfaceAttachment(
			"MyPrivateEniAttachmentB",
			DeviceIndex = "1",
			InstanceId = Ref(instance_priv_sub_b),
			NetworkInterfaceId = Ref(my_private_eni_b)
		))


		# load balancer add security group and target to instances

		elastic_load_balancer = self.template.add_resource(elb.LoadBalancer(
			'ElasticLoadBalancer',
	        AccessLoggingPolicy=elb.AccessLoggingPolicy(
	        EmitInterval=5,
	        Enabled=True,
	        S3BucketName="logging",
	        S3BucketPrefix="myELB",
	      ),
		   AvailabilityZones=GetAZs(""),
	       ConnectionDrainingPolicy=elb.ConnectionDrainingPolicy(
	       Enabled=True,
	       Timeout=300,
	      ),
	       CrossZone=True,
	       Instances=[Ref(r) for r in web_server_instances],
		   Listeners=[
	            elb.Listener(
	                LoadBalancerPort="443",
	                InstancePort=Ref(self.load_balancer_port),
	                Protocol="HTTPS",
	         )
	        ],
			Subnets = [Ref(pub_subnet_a),Ref(pub_subnet_b)],
	        HealthCheck=elb.HealthCheck(
	            Target=Join("", ["HTTPS:", Ref(self.load_balancer_port), "/"]),
	            HealthyThreshold="3",
	            UnhealthyThreshold="5",
	            Interval="30",
	            Timeout="5",
	        )
	    ))

		# autoscaling Group
		auto_scale = self.template.add_resource(autoscaling.AutoScalingGroup(
				"AutoScalingGroup",
				LaunchConfigurationName = "LaunchConfiguration",
				LoadBalancerNames = Ref(elastic_load_balancer),
				VPCZoneIdentifier = [Ref(pub_subnet_a),Ref(pub_subnet_b)],
				MinSize = "1",
				MaxSize = "3",
				UpdatePolicy = policies.UpdatePolicy(
					AutoScalingRollingUpdate = policies.AutoScalingRollingUpdate(
						PauseTime = "PT10M",
						MaxBatchSize = "1",
						MinInstancesInService = "1"
					)
				)
		))

		#route 53
		#public hosted zone
		public_hosted_zone = self.template.add_resource(CustomRoute53ZoneInfo(
				"CustomResource",
				ServiceToken = "MyToken",
				DomainName = "MyDomain",
				PrivateZone = False
		))

		#route53 record
		public_record = self.template.add_resource(route53.RecordSetType(
				"MyPublicRecord",
				AliasTarget = route53.AliasTarget(
					DNSName = Ref(elastic_load_balancer),
					HostedZoneId = Ref(elastic_load_balancer)
				),
				HostedZoneId = Ref(public_hosted_zone),
				Name = "MyPublicRecord-us-east-1-a",
				Type = "A"
		))
		##########
		# output #
		##########

		self.setOutput("MyVpcId", Ref(my_vpc))
		self.setOutput("PublicSubnetAId", Ref(pub_subnet_a))
		self.setOutput("PublicSubnetBId", Ref(pub_subnet_b))
		self.setOutput("PubSubnetsList", Join(",",[ Ref(pub_subnet_a), Ref(pub_subnet_b)]))
		self.setOutput("PrivateSubnetAId", Ref(priv_subnet_a))
		self.setOutput("PrivateSubnetBId", Ref(priv_subnet_b))
		self.setOutput("PrivSubnetsList", Join(",",[ Ref(priv_subnet_a), Ref(priv_subnet_b)]))
		self.setOutput("PrivSubnetCidrA", Select(0, Ref(self.priv_subnet_cidrs)))
		self.setOutput("PrivSubnetCidrB", Select(1, Ref(self.priv_subnet_cidrs)))
		self.setOutput("PubSubnetCidrA", Select(0, Ref(self.pub_subnet_cidrs)))
		self.setOutput("PubSubnetCidrB", Select(1, Ref(self.pub_subnet_cidrs)))

	def generateTemplate(self):
		print(self.template.to_yaml())
		self.addParams()
		self.addResources()
		filename = os.path.splitext(os.path.basename(sys.argv[0]))[0]
		destination = os.path.abspath(os.path.join(os.path.abspath(__file__), "../..", "templates"))

		if not os.path.exists(destination):
        		os.mkdir(destination, mode=0o777)
        		print('Template directory generated: %s' % destination)
		filepath = '%s/%s.yaml' % (destination, filename)
		file = open(filepath, 'w')
		file.write(self.template.to_yaml())
		file.close()
		print('CloudFormation Template generated: %s' % filepath)




networkingtemplate = NetworkingTemplate()
networkingtemplate.generateTemplate()
