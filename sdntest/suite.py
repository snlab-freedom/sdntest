#!/usr/bin/env python

import docker
import logging
from os import path
from time import sleep
from sdntest.exception import PlatformException, WorkspaceException

class TestSuite():

    def __init__(self, configs):
        self.docker = docker.from_env()
        self.logger = logging.getLogger("TestSuite")
        # container instance
        self.controller = None
        self.mininet = None
        # testcase options
        self.workspace = ""
        self.repeat = 0
        self.platform = "odl"
        self.release_tag = ""
        self.apps = ""
        self.waiting_time = 15
        self.net_workflow = None
        # default values
        self.default_odl_features = ' '.join([
            'odl-openflowplugin-southbound',
            'odl-openflowplugin-flow-services'
        ])
        self.default_onos_apps = "openflow"
        self.setup(configs)

    def bootstrap_odl(self, release_tag="4.4.0"):
        """
        Bootstrap a container for a specified OpenDaylight release distribution.

        Args:
            release_tag (str): the release version of the distribution.
        """
        image_tag = "opendaylight/odl:" + release_tag
        self.controller = self.docker.containers.run(image_tag,
                                                     command="/opt/opendaylight/bin/karaf",
                                                     tty=True,
                                                     detach=True)
        odl_features = self.apps if self.apps else self.default_odl_features
        self.controller.exec_run('/opt/opendaylight/bin/client -u karaf "feature:install %s"' % self.apps)

    def bootstrap_onos(self, release_tag="latest"):
        """
        Bootstrap a container for a specified ONOS release distribution.

        Args:
            release_tag (str): the release version of the distribution.
        """
        image_tag = "onosproject/onos:" + release_tag
        onos_apps = self.apps if self.apps else self.default_onos_apps
        self.controller = self.docker.containers.run(image_tag,
                                                     tty=True,
                                                     detach=True,
                                                     environment={
                                                         'ONOS_APPS': onos_apps
                                                     })
        raw_active_apps = self.controller.exec_run('client "apps -a -s"')
        active_apps = '\n'.join(active_apps.split('\n')[1:])
        self.logger.info("Following apps have been installed:\n%s", active_apps)

    def bootstrap_platfrom(self):
        """
        Bootstrap a container for a given SDN controller platform.
        """
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
                },
                self.testcase_path: {
                    'bind': '/experiment',
                    'mode': 'rw'
                }
            },
            'privileged': True,
            'tty': True
        }
        net_workflow_command = path.join('/experiment', self.net_workflow)
        self.mininet = self.docker.containers.run(controller_ip,
                                                  command=net_workflow_command,
                                                  **opts)

    def kill_platform(self):
        self.controller.stop()
        self.controller.remove()

    def setup(self, configs):
        """
        Set options from configs object

        Args:
            configs (dict): json object of testcase configuration file.
        """
        if 'workspace' in configs.keys():
            self.workspace = configs['workspace']
        else:
            self.logger.error('Missing workspace. You need to set a experiment workspace directory to run the testcase.')
            raise WorkspaceException()
        if not path.isdir(self.workspace):
            self.logger.error('Workspace %s is non-existed or not a directory', self.workspace)
            raise WorkspaceException(self.workspace)

        if 'repeat' in configs.keys():
            self.repeat = configs['repeat']
        if 'platform' in configs.keys():
            self.platform = configs['platform']
        if 'release' in configs.keys():
            self.release_tag = configs['release']
        if 'apps' in configs.keys():
            self.apps = configs['apps']
        if 'waiting' in configs.keys():
            self.waiting_time = configs['waiting']
        if 'workflow' in configs.keys():
            self.net_workflow = configs['workflow']

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
