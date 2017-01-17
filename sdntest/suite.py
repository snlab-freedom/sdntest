#!/usr/bin/env python2

import docker
import logging
from time import sleep
from nettest.exception import PlatformException

class TestSuite():

    def __init__(self, testcase_dir):
        self.docker = docker.from_env()
        self.logger = logging.getLogger("TestSuite")
        self.controller = None
        self.mininet = None
        self.repeat = 0
        self.platform = "odl"
        self.release_tag = ""
        self.waiting_time = 15
        self.net_workflow = None

    def bootstrap_odl(self, release_tag="4.4.0"):
        """
        Bootstrap a container for a specified OpenDaylight release distribution.
        """
        image_tag = "opendaylight/odl:" + release_tag
        self.controller = self.docker.containers.run(image_tag,
                                                     command="/opt/opendaylight/bin/karaf")

    def bootstrap_onos(self, release_tag="latest"):
        """
        Bootstrap a container for a specified ONOS release distribution.
        """
        image_tag = "onosproject/onos:" + release_tag
        self.controller = self.docker.containers.run(image_tag)

    def bootstrap_platfrom(self):
        if "odl" == self.platform:
            if self.release_tag:
                self.bootstrap_odl(self.release_tag)
            else:
                self.bootstrap_odl()
        elif "onos" == self.platform:
            if self.release_tag:
                self.bootstrap_onos(self.release_tag)
            else:
                self.bootstrap_onos()
        else:
            self.logger.error("Unknown or unsupported SDN controller platform: %s",
                              self.platform)
            raise PlatformException(self.platform)

    def bootstrap_mininet(self):
        """
        Bootstrap a container for mininet and execute a given script
        to emulate network workflow.
        """
        controller_ip = self.controller.attrs['NetworkSettings']['IPAddress']
        mininet_image = "ciena/mininet"
        opts = {
            'cap_add': ['NET_ADMIN', 'SYS_MODULE'],
            'volumes': {
                '/lib/modules': {
                    'bind': '/lib/modules',
                    'mode': 'rw'
                }
            },
            'privileged': True
        }
        self.mininet = self.docker.containers.run(controller_ip,
                                                  command=self.net_workflow,
                                                  **opts)

    def kill_platform(self):
        self.controller.stop()
        self.controller.remove()

    def setup(self):
        """
        """
        pass

    def run(self):
        """
        Repeatedly execute test case.
        """
        for i in range(self.repeate):
            self.logger.info("Bootstrapping SDN platform...")
            self.bootstrap_platform()
            self.logger.info("Bootstrapped SDN platform")
            self.logger.info("Waiting for mandatory components loaded...")
            sleep(self.waiting_time)
            self.bootstrap_mininet()
            self.kill_platform()
