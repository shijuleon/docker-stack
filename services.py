import time, sys, signal

import docker
client = docker.from_env()

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

    def run_image(self, image, name, network, detach = True):
        running_container = client.containers.run(image=image, name=name, hostname=name, network=network, detach=detach)
        self.containers.append(running_container)
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

example_app = Stack(name='example-app')

# Create a new network
example_app_network = example_app.create_network('example-app')

# List networks
print(example_app.list_networks())

# Run services
redis_container = example_app.run_image(image='redis', name='example-redis', network=example_app_network.name)
rabbitmq_container = example_app.run_image(image='rabbitmq', name='example-rabbitmq', network=example_app_network.name)

redis_container.reload()
print(redis_container.attrs['NetworkSettings']['Networks']['example-app']['IPAddress'])

# List containers
print(example_app.list_containers())

def signal_handler(sig, frame):
    if sig == signal.SIGINT:
        on_interrupt()
            
def on_interrupt():
    print("Destroying stack: %s" % example_app.name)
    example_app.destroy_stack()

signal.signal(signal.SIGINT, signal_handler)
signal.pause()