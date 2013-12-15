do
======

Manage Digital Ocean droplets with ease.

### Setup

* Copy the scripts in bin to wherever you want them. Ensure that "do" is on your path.
* Create a ~/.digitalocean file, the contents should be:

        export DO_CLIENT_ID=e15...
        export DO_API_KEY=825a...
        export DO_ROOT_KEY=/path/to/ssh/key   # private key that allows root to ssh into new droplets

* Run the install-packages.sh script to install the required python modules (this uses apt-get; for other package managers it'll be a little different)

### Machines
Digital Ocean droplets have a number of parameters that must be specified at time of creation and can never change thereafter.
Things like region, size, image (operating system), etc.

This utility uses simple yaml files, called machine files, to capture this data.

An example machine file is in machines/dev.yml, duplicated here:

    size_id: 2GB
    image_id: Ubuntu 13.10 x64
    region_id: New York 2
    ssh_key_ids: [ dev ]
    virtio: false
    private_networking: false

Copy this machines directory somewhere, and set your DO_MACHINES environment variable to point to it.
Note that you can create machines with an absolute path to a machine file (see "do create" below), but it's often easier to use a simple symbolic name.

### Usage

##### List all images

        do images
##### List all regions

        do regions
##### List all sizes

        do sizes
##### List all ssh keys

        do keys
##### List all droplets
These are equivalent:

        do droplets
        do list

##### Create a new droplet

        do create machine-type name
For example:

        do create prod-nginx nginx14
        do create /absolute/path/to/prod-nginx.yml nginx14
The first example above creates a new droplet named nginx14 based on the machine file ${DO_MACHINES}/prod-nginx.yml

The second example above creates a new droplet named nginx14 based on the machine file /absolute/path/to/prod-nginx.yml


#####  Bootstrap a droplet (only tested on Ubuntu)
Bootstrapping will remove the root-access SSH key you used to create the machine, and replace
it with a regular user who can login via ssh without using a password (but using the given ssh public key), and
has sudo access without requiring a password.

        do bootstrap nginx14 myuser ~/path/to/myuser/.ssh/key.pub
For this command to work, you must have DO_ROOT_KEY defined in either ~/.digitalocean or your shell environment.

##### View a droplet
These are all equivalent, and will show a pretty-printed JSON representation of the droplet:

        do droplets nginx14
        do droplet nginx14
        do inspect nginx14
        do view nginx14
        do show nginx14

##### Print a droplet's IP
This will print just the droplet's IP address, and is useful in script where you want to do something with $(do droplet-ip ${something})

        do droplet-ip nginx14

##### SSH to a droplet
This will only work if you bootstrapped the droplet using "do bootstrap":

        do ssh nginx14

##### Destroy a droplet
!!! **There is no "are you sure" asked here, your droplet WILL BE DESTROYED when you hit Enter** !!!

        do destroy nginx14

##### Developer access
Enter a python console with all functions/variables in context, for development and/or debugging purposes:

        do console
