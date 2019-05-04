import time, sys, signal
from jinja2 import Template

import docker
client = docker.from_env()

def signal_handler(sig, frame):
    if sig == signal.SIGINT:
        on_interrupt()
            
def on_interrupt():
    print("Destroying stack: %s" % example_app.name)
    example_app.destroy_stack()

class Stack:

    def __init__(self, name):
        self.name = name
        self.containers = []
        self.networks = []

    def create_network(self, name):
        created_network = client.networks.create(name, driver='bridge')
        self.networks.append(created_network)
        return created_network

    def list_networks(self):
        return [n.name for n in self.networks]

    def run_image(self, image, name, network, volumes={}, ports={}, environment={}, detach=True):
        running_container = client.containers.run(image=image, name=name, hostname=name, network=network, volumes=volumes, environment=environment, ports=ports, detach=detach)
        self.containers.append(running_container)
        running_container.reload()
        return running_container

    def list_containers(self):
        return [c.name for c in self.containers]
    
    def stop_containers(self, containers):
        for c in containers:
            c.stop()

    def remove_networks(self, networks):
        for n in networks:
            n.remove()

    def remove_containers(self, containers):
        for c in containers:
            c.remove()

    def destroy_stack(self):
        self.stop_containers(self.containers)
        self.remove_containers(self.containers)
        self.remove_networks(self.networks)

    def get_container_logs(self, container):
        return container.logs()

class CustomService:
	
    def __init__(self, name, environment_file="", template_variables={}):
        self.name = name
        self.environment = {}
        self.environment_file = environment_file
        self.template_variables = {}
        self.render_env(template_variables)

    def read_env_file(self):
        with open(self.environment_file+'.rendered', 'r') as f:
            lines = f.readlines()
		
        for l in lines:
            values = l.split('=', 1)
            self.environment[values[0].strip()] = values[1].strip()

        return self.environment
	
    def add_template_variables(self, variables):
        self.template_variables.update(variables)

    def write_template_variables(self):
        with open(self.environment_file, 'r') as f:
            template = Template(f.read())

        rendered = template.render(self.template_variables)

        with open(self.environment_file+'.rendered', 'w') as f:
            f.write(rendered)

    def render_env(self, template_variables):
        self.add_template_variables(template_variables)
        self.write_template_variables()
        self.read_env_file()


# Stack: consists of a network, containers

example_app = Stack(name='example-app')

# Create a new network
example_app_network = example_app.create_network('example-app')

# Run services
redis_container = example_app.run_image(image='redis', name='redis-latest', network=example_app_network.name)
rabbitmq_container = example_app.run_image(image='rabbitmq', name='rabbitmq-latest', network=example_app_network.name)

redis_host = redis_container.attrs['NetworkSettings']['Networks']['example-app']['IPAddress']
rabbitmq_host = rabbitmq_container.attrs['NetworkSettings']['Networks']['example-app']['IPAddress']

# Create a custom service
template_variables = {'REDIS_HOST': redis_host, 'EVENT_QUEUE_URL': rabbitmq_host}
custom_service_1 = CustomService(name='custom_service_1', environment_file='/home/shiju/go/src/github.com/shijuleon/custom_service_1/docker-dev.env', template_variables=template_variables)

# Wait for redis and rabbitmq to come up
time.sleep(10)
custom_service_1_container = example_app.run_image(image='custom_service_1', name='custom_service_1', network=example_app_network.name, environment=custom_service_1.environment, ports={'5881':5881})
custom_service_1_host = custom_service_1_container.attrs['NetworkSettings']['Networks']['example-app']['IPAddress']

template_variables = {'APP_URL': custom_service_1_host+':5881', 'CONF_URL': custom_service_1_host+':5881'}
custom_service_2 = CustomService(name='custom_service_2', environment_file='/home/shiju/go/src/github.com/shijuleon/custom_service_2/custom_service_2-dev.env', template_variables=template_variables)

custom_service_2_1_volumes = {'/home/shiju/Dev/example/mounts/custom_service_2-1/storage/files': {'bind': '/storage/files', 'mode':'rw'}, '/home/shiju/Dev/example/mounts/custom_service_2-1/conf/': {'bind': '/conf', 'mode':'rw'}}
custom_service_2_1_container = example_app.run_image(image='custom_service_2', name='custom_service_2_1', network=example_app_network.name, environment=custom_service_2.environment, volumes=custom_service_2_1_volumes)

custom_service_2_2_volumes = {'/home/shiju/Dev/example/mounts/custom_service_2-2/storage/files': {'bind': '/storage/files', 'mode':'rw'}, '/home/shiju/Work/example/mounts/custom_service_2-2/conf/': {'bind': '/conf', 'mode':'rw'}}
custom_service_2_2_container = example_app.run_image(image='custom_service_2', name='custom_service_2_2', network=example_app_network.name, environment=custom_service_2.environment, volumes=custom_service_2_2_volumes)

# List containers
print(example_app.list_containers())

signal.signal(signal.SIGINT, signal_handler)
signal.pause()