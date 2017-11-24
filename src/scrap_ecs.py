#!/usr/bin/env python
from __future__ import with_statement, print_function

from boto import ec2
from boto import ec2containerservice

import os
import logging
import json
from time import sleep


def save_tasks_for_cluster(tasks, ecsIdToinstancePrivateIp, cluster):
    # append
    services = []
    for task in tasks:
        for container in task['containers']:
            labels = {
                'container': container['name'],
                'taskArn': container['taskArn'],
                'group': task['group']
            }
            for network in container['networkBindings']:
                labels['containerPort'] = "%s" % network['containerPort']
                ecsInst = ecsIdToinstancePrivateIp[task['containerInstanceArn']]
                labels['host'] = ecsInst['instance_id']
                target = "%s:%s" % (ecsInst['private_ip_address'], network['hostPort'])
                services.append({
                    'targets': [target],
                    'labels': labels
                })

    # save json
    directory = os.environ.get("PATH_TO_SAVE")
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open("%s/%s.json" % (directory, cluster), 'w') as outfile:
        json.dump(services, outfile)


def get_for_cluster(ecscli, ec2cli, cluster):
    res = ecscli.list_container_instances(cluster=cluster)
    container_instances = res['ListContainerInstancesResponse']['ListContainerInstancesResult']['containerInstanceArns']
    container_instances_desc = \
    ecscli.describe_container_instances(container_instances, cluster)['DescribeContainerInstancesResponse'][
        'DescribeContainerInstancesResult']['containerInstances']

    instanceIdToEcsId = {}
    ecsIdToinstancePrivateIp = {}

    for val in container_instances_desc:
        instanceIdToEcsId[val['ec2InstanceId']] = val['containerInstanceArn']

    for val in ec2cli.get_all_network_interfaces():
        if instanceIdToEcsId.has_key(val.attachment.instance_id):
            ecsIdToinstancePrivateIp[instanceIdToEcsId[val.attachment.instance_id]] = {
                'private_ip_address': val.private_ip_address, 'instance_id': val.attachment.instance_id
            }

    tasksIds = ecscli.list_tasks(cluster=cluster)['ListTasksResponse']['ListTasksResult']['taskArns']
    tasks = ecscli.describe_tasks(tasksIds, cluster=cluster)['DescribeTasksResponse']['DescribeTasksResult']['tasks']
    save_tasks_for_cluster(tasks, ecsIdToinstancePrivateIp, cluster)


def scrap(aws_region, clusters):
    ec2cli = ec2.connect_to_region(aws_region)
    ecscli = ec2containerservice.connect_to_region(aws_region)

    try:
        for val in clusters:
            get_for_cluster(ecscli, ec2cli, val)
    except Exception as ex:
        logging.error("Can't scrape %s, region %s, clusters %s" % ex, aws_region, clusters)


if __name__ == "__main__":
    aws_region = os.environ.get("AWS_REGION")
    clusters = os.environ.get("ECS_CLUSTERS").split(",")

    logging.basicConfig(level="INFO")
    print("Starting aws_region=%s, clusters=%s" % (aws_region, clusters))
    while True:
        try:
            scrap(aws_region, clusters)
        except Exception as ex:
            logging.error("Can't scrape %s" % ex)
        sleep(60)
