from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EC2RunInstancesRequest(BaseModel):
    """Request schema for ec2.run_instances()."""

    ImageId: str
    MinCount: int = 1
    MaxCount: int = 1
    InstanceType: str | None = None
    KeyName: str | None = None
    SecurityGroupIds: list[str] | None = None
    SecurityGroups: list[str] | None = None
    SubnetId: str | None = None
    UserData: str | None = None
    IamInstanceProfile: dict[str, str] | None = None
    BlockDeviceMappings: list[dict[str, object]] | None = None
    TagSpecifications: list[dict[str, object]] | None = None
    DryRun: bool | None = None
    ClientToken: str | None = None


class EC2InstanceState(BaseModel):
    """EC2 instance state."""

    Code: int | None = None
    Name: str | None = None


class EC2Instance(BaseModel):
    """EC2 instance from run_instances/describe_instances response."""

    InstanceId: str | None = None
    InstanceType: str | None = None
    State: EC2InstanceState | None = None
    Architecture: str | None = None
    LaunchTime: datetime | None = None
    Placement: dict[str, str] | None = None
    PrivateIpAddress: str | None = None
    PublicIpAddress: str | None = None
    SubnetId: str | None = None
    VpcId: str | None = None
    ImageId: str | None = None
    KeyName: str | None = None
    SecurityGroups: list[dict[str, str]] | None = None
    Tags: list[dict[str, str]] | None = None


class EC2RunInstancesResponse(BaseModel):
    """Response from ec2.run_instances()."""

    ReservationId: str | None = None
    OwnerId: str | None = None
    Instances: list[EC2Instance] | None = None
    Groups: list[dict[str, str]] | None = None


class EC2DescribeInstancesRequest(BaseModel):
    """Request schema for ec2.describe_instances()."""

    InstanceIds: list[str] | None = None
    Filters: list[dict[str, list[str]]] | None = None
    MaxResults: int | None = None
    NextToken: str | None = None
    DryRun: bool | None = None


class EC2Reservation(BaseModel):
    """Reservation from describe_instances."""

    ReservationId: str | None = None
    OwnerId: str | None = None
    Instances: list[EC2Instance] | None = None
    Groups: list[dict[str, str]] | None = None


class EC2DescribeInstancesResponse(BaseModel):
    """Response from ec2.describe_instances()."""

    Reservations: list[EC2Reservation] | None = None
    NextToken: str | None = None


class EC2StartInstancesRequest(BaseModel):
    """Request for ec2.start_instances()."""

    InstanceIds: list[str]
    DryRun: bool | None = None


class EC2StopInstancesRequest(BaseModel):
    """Request for ec2.stop_instances()."""

    InstanceIds: list[str]
    Force: bool | None = None
    DryRun: bool | None = None


class EC2TerminateInstancesRequest(BaseModel):
    """Request for ec2.terminate_instances()."""

    InstanceIds: list[str]
    DryRun: bool | None = None


class EC2InstanceStateChange(BaseModel):
    """Instance state change from start/stop/terminate."""

    InstanceId: str | None = None
    CurrentState: EC2InstanceState | None = None
    PreviousState: EC2InstanceState | None = None


class EC2StartStopTerminateResponse(BaseModel):
    """Response from start_instances, stop_instances, terminate_instances."""

    StartingInstances: list[EC2InstanceStateChange] | None = None
    StoppingInstances: list[EC2InstanceStateChange] | None = None
    TerminatingInstances: list[EC2InstanceStateChange] | None = None
