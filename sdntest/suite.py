#!/usr/bin/env python

import os
import sys
import docker
import logging
import json
if sys.version[0] == '2':
    import Queue as queue
else:
    import queue
from time import sleep
from threading import Thread
from docker.errors import ImageNotFound
from sdntest.exception import PlatformException, WorkspaceException, REASON
from sdntest.utils import green, cyan

class TestSuite(Thread):

    def __init__(self, configs):
        Thread.__init__(self)
        self.exc_pool = queue.Queue()
        self.docker = docker.from_env()
        self.logger = logging.getLogger("TestSuite")
        # container instance
        self.controller = None
        # self.mininet = None
        # testcase options
        self.workspace = ""
        self.outputdir = ""
        self.outputcnt = 0
        self.repeat = 0
        self.platform = "odl"
        self.release_tag = ""
        self.apps = ""
        self.waiting_time = 15
        self.net_workflow = None
        self.arguments = ""
        self.arglist = False
        self.argcnt = 0
        # parallel options
        self.parallel = 0
        self.group = 0
        # default values
        self.default_odl_features = ' '.join([
            'odl-openflowplugin-southbound',
            'odl-openflowplugin-flow-services'
        ])
        self.default_onos_apps = "openflow,proxyarp"
        self.setup(configs)

    def prepare_image(self, image):
        """
        Pull docker image from dockerhub.
        """
        for line in self.docker.api.pull(image, stream=True):
            status_info = json.loads(line)
            status = status_info['status']
            progress = status_info.get('progress', '')
            sys.stdout.write('\r\033[K%s %s' % (status, progress))
        self.logger.info('Pulling image %s finished!', image)

    def bootstrap_odl(self, release_tag="4.4.0"):
        """
        Bootstrap a container for a specified OpenDaylight release distribution.

        Args:
            release_tag (str): the release version of the distribution.
        """
        image_tag = "opendaylight/odl:" + release_tag

        try:
            self.docker.images.get(image_tag)
        except ImageNotFound:
            self.logger.info("Image %s not found. Try to pull the image from dockerhub...", image_tag)
            self.prepare_image(image_tag)

        self.logger.info("Starting container from image %s", image_tag)
        self.controller = self.docker.containers.run(image_tag,
                                                     command="/opt/opendaylight/bin/karaf",
                                                     tty=True,
                                                     detach=True)
        sleep(5)

        odl_features = self.apps if self.apps else self.default_odl_features
        self.logger.info("Installing the following features: %s", odl_features)
        self.controller.exec_run('/opt/opendaylight/bin/client -u karaf "feature:install %s"' % odl_features)

    def bootstrap_onos(self, release_tag="latest"):
        """
        Bootstrap a container for a specified ONOS release distribution.

        Args:
            release_tag (str): the release version of the distribution.
        """
        image_tag = "onosproject/onos:" + release_tag
        onos_apps = self.apps if self.apps else self.default_onos_apps

        self.logger.info("Starting container from image %s", image_tag)
        self.controller = self.docker.containers.run(image_tag,
                                                     tty=True,
                                                     detach=True,
                                                     environment={
                                                         'ONOS_APPS': onos_apps
                                                     })
        raw_active_apps = self.controller.exec_run('client "apps -a -s"')
        active_apps = '\n'.join(raw_active_apps.split('\n')[1:])
        self.logger.info("Following apps have been installed:\n%s", active_apps)

    def bootstrap_platform(self):
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
        self.controller.reload()
        controller_ip = self.controller.attrs['NetworkSettings']['IPAddress']
        mininet_image = "ciena/mininet:latest"

        try:
            self.docker.images.get(mininet_image)
        except ImageNotFound:
            self.logger.info("Image %s not found. Try to pull the image from dockerhub...", mininet_image)
            self.prepare_image(mininet_image)

        opts = {
            'cap_add': ['NET_ADMIN', 'SYS_MODULE'],
            'volumes': {
                '/lib/modules': {
                    'bind': '/lib/modules',
                    'mode': 'rw'
                },
                self.workspace: {
                    'bind': '/data',
                    'mode': 'rw'
                }
            },
            'privileged': True,
            'remove': True,
            'tty': True
        }
        net_workflow_command = '%s %s' % (os.path.join('/data', self.net_workflow),
                                          controller_ip + ' ' + self.arguments)
        self.logger.info("Executing testcase by using workflow command: %s", net_workflow_command)
        workflow_output = self.docker.containers.run(mininet_image,
                                                     command=net_workflow_command,
                                                     **opts)
        self.outputcnt += 1
        self.logger.info("Workflow finished: (%d/%d)", self.outputcnt, self.repeat)
        if self.parallel > 1:
            if self.arglist:
                outputfile = 'output.%d.%d-%d.log' % (self.group, self.argcnt, self.outputcnt)
            else:
                outputfile = 'output.%d.%d.log' % (self.group, self.outputcnt)
        else:
            if self.arglist:
                outputfile = 'output.%d-%d.log' % (self.argcnt, self.outputcnt)
            else:
                outputfile = 'output.%d.log' % self.outputcnt

        outputfile = os.path.join(self.outputdir, outputfile)
        with open(outputfile, 'w') as f:
            f.write(workflow_output)
            self.logger.info("Result saved in %s", outputfile)

    def kill_platform(self):
        """
        Stop and remove the platform container.
        """
        self.logger.info("Stopping SDN platform container...")
        self.controller.stop()
        self.logger.info(green(u"\u2714") + " Container %s is stopped!", self.controller.id)
        self.logger.info("Removing SDN platform container...")
        self.controller.remove()
        self.logger.info(green(u"\u2714") + " Container %s is removed!", self.controller.id)

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
        if not os.path.isdir(self.workspace):
            self.logger.error('Workspace %s is non-existed or not a directory', self.workspace)
            raise WorkspaceException(self.workspace)

        self.outputdir = os.path.join(self.workspace, 'output')
        if not os.path.exists(self.outputdir):
            os.mkdir(self.outputdir)
        if not os.path.isdir(self.outputdir):
            self.logger.error("'output' has been existing, but not a directory.")
            raise WorkspaceException(self.workspace, reason=REASON['OUTDIR'])

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
        if 'arguments' in configs.keys():
            self.arguments = configs['arguments']

        if 'parallel' in configs.keys():
            self.parallel = configs['parallel']
        if 'group' in configs.keys():
            self.group = configs['group']

    def run(self):
        """
        Repeatedly execute test case.
        """
        try:
            self.logger.info("Starting execution...")

            if type(self.arguments) == list:
                argumentsList = self.arguments
                self.arglist = True
            else:
                argumentsList = [ self.arguments ]

            for arguments in argumentsList:
                self.arguments = arguments
                self.argcnt += 1
                self.logger.info(cyan(">>> Arguments: %s"), self.arguments)
                self.outputcnt = 0
                for i in range(self.repeat):
                    self.logger.info("Repeat counter: %d", i+1)
                    self.logger.info("Bootstrapping SDN platform...")
                    self.bootstrap_platform()
                    self.logger.info(green(u"\u2714") + " Bootstrapped SDN platform")
                    self.logger.info("Waiting for mandatory components loaded...")
                    sleep(self.waiting_time)
                    self.logger.info("Bootstrapping Mininet...")
                    self.bootstrap_mininet()
                    self.logger.info(green(u"\u2714") + " Mininet test finished")
                    self.logger.info("Cleaning up SDN platform...")
                    self.kill_platform()
                    self.logger.info(green(u"\u2714") + " Environment is clean")
        except Exception:
            self.exc_pool.put(sys.exc_info())
            import traceback
            stackTrace = traceback.format_exc()
            self.logger.debug(stackTrace + "\n")
