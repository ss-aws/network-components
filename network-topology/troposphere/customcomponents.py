import troposphere.cloudformation as cloudformation

class CustomRoute53ZoneInfo(cloudformation.AWSCustomObject):
    resource_type = "Custom::CustomRoute53ZoneInfo"
    props = {
        "DomainName" : (str, True),
        "PrivateZone" : (bool, True),
        "Tags" : (list, False)

    }
