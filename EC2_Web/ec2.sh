#!/bin/bash

# Define variables
KEY_NAME="abc" # Replace with your key pair name
SECURITY_GROUP_NAME="web1-sg"
INSTANCE_TYPE="t2.micro"
AMI_ID="ami-06b21ccaeff8cd686" # Amazon Linux 2 AMI (check region specific AMI)
USER_DATA_SCRIPT="#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo '<html><h1>مرحبا بكم بيننا</h1></html>' > /var/www/html/index.html"
INSTANCE_NAME="FreeTierWebServer"

# Create a key pair if it doesn't exist already
aws ec2 create-key-pair --key-name $KEY_NAME --query 'KeyMaterial' --output text > ${KEY_NAME}.pem
chmod 400 ${KEY_NAME}.pem

# Check if the security group already exists
SECURITY_GROUP_ID=$(aws ec2 describe-security-groups --group-names "$SECURITY_GROUP_NAME" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)

# If the security group doesn't exist, create a new one
if [ "$SECURITY_GROUP_ID" == "None" ]; then
  echo "Security group does not exist. Creating a new one..."
  SECURITY_GROUP_ID=$(aws ec2 create-security-group --group-name "$SECURITY_GROUP_NAME" --description "Security group for web server" --query 'GroupId' --output text)
else
  echo "Using existing security group: $SECURITY_GROUP_ID"
fi

echo "Security Group ID: $SECURITY_GROUP_ID"
# Allow inbound traffic on port 80 (HTTP) from anywhere
set +e  # Disable immediate exit on error
aws ec2 authorize-security-group-ingress --group-id $SECURITY_GROUP_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 2>/dev/null
if [ $? -ne 0 ]; then
  echo "The security group rule already exists, skipping adding it again."
else
  echo "Added inbound rule to allow HTTP traffic on port 80."
fi
set -e  # Re-enable immediate exit on error
# Launch the EC2 instance with user data for launching a simple website
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --count 1 \
  --instance-type $INSTANCE_TYPE \
  --key-name $KEY_NAME \
  --security-group-ids $SECURITY_GROUP_ID \
  --user-data "$USER_DATA_SCRIPT" \
  --query 'Instances[0].InstanceId' \
  --output text)

# Tag the instance with a name
aws ec2 create-tags --resources $INSTANCE_ID --tags Key=Name,Value=$INSTANCE_NAME

# Wait for the instance to be running
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Get the public IP address of the instance
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

# Print the public IP address
echo "EC2 instance launched successfully!"
echo "You can access the website at: http://$PUBLIC_IP"
