#!/usr/bin/python

import sys
import os
import code
import yaml
import json
import requests
import time
import re
import subprocess
import socket

API_BASE = 'https://api.digitalocean.com'

# from http://stackoverflow.com/questions/106179/regular-expression-to-match-hostname-or-ip-address
ValidIpAddressRegex = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$";
ValidHostnameRegex = "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$";

auth = { 'client_id': sys.argv[1], 'api_key': sys.argv[2] }

command = sys.argv[3]
args = sys.argv[4:]

def load_yaml (yml):
    with open(yml, 'r') as stream:
        return yaml.load(stream)

def pretty_print_json (data):
    print json.dumps(json.loads(data), sort_keys=True, indent=4, separators=(',', ': '))

def find_id_for_name(json_string, name, list_element):
    elements = json.loads(json_string)[list_element]
    for element in elements:
        if element['name'] == name:
            return element['id']
    return None

def execute_shell_internal(args):
    env = os.environ

    # force the first argument to be a fully-qualified path, correcting it when it's a relative path
    for path in os.environ['PATH'].split(':'):
        if os.path.exists(path+"/"+args[0]):
            args[0] = path + "/" + args[0]

    print >> sys.stderr, ">>> execute_shell ("+str(args)+") with env="+str(env)
    child = subprocess.check_call(args, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    return child

def get_images (auth):
    return requests.get(API_BASE+'/images', params=auth).text

def find_image_id (auth, name):
    return find_id_for_name(get_images(auth), name, 'images')

def get_regions (auth):
    return requests.get(API_BASE+'/regions', params=auth).text

def find_region_id (auth, name):
    return find_id_for_name(get_regions(auth), name, 'regions')

def get_sizes (auth):
    return requests.get(API_BASE+'/sizes', params=auth).text

def find_size_id (auth, name):
    return find_id_for_name(get_sizes(auth), name, 'sizes')

def get_keys (auth):
    return requests.get(API_BASE+'/ssh_keys', params=auth).text

def find_key_id (auth, name):
    return find_id_for_name(get_keys(auth), name, 'ssh_keys')

def get_droplets(auth):
    return requests.get(API_BASE+'/droplets', params=auth).text

def find_droplet_id(auth, name):
    return find_id_for_name(get_droplets(auth), name, 'droplets')

def find_droplet_by_id(auth, id):
    return requests.get(API_BASE+'/droplets/'+str(id), params=auth).text

def find_droplet_by_name(auth, name):
    return find_droplet_by_id(auth, find_droplet_id(auth, name))

def get_droplet_ip(auth, name):
    if re.match(ValidIpAddressRegex, name):
        return name
    return json.loads(find_droplet_by_name(auth, name))['droplet']['ip_address']

def ssh(args):
    args.insert(0, 'ssh')
    try:
        execute_shell_internal(args)
    except subprocess.CalledProcessError as e:
        print str(e)

def load_machine(mtype):
    if "/" in mtype:
        return load_yaml(mtype)
    machines_dir = os.environ['DO_MACHINES']
    if machines_dir is None:
        print "No DO_MACHINES env var defined, can't find machine "+mtype
    return load_yaml(machines_dir + "/" + mtype + ".yml")

if command == "console":
    code.interact(local=locals())

elif command == "images":
    pretty_print_json(get_images(auth))

elif command == "regions":
    pretty_print_json(get_regions(auth))

elif command == "sizes":
    pretty_print_json(get_sizes(auth))

elif command == "keys":
    pretty_print_json(get_keys(auth))

elif command == "ssh":
    if len(args) == 0:
        print "ssh requires  1 arg (droplet ip or name)"
        sys.exit(1)
    ip = args[0]
    user_clause = ""
    if not re.match(ValidIpAddressRegex, ip):
        try:
            ip = get_droplet_ip(auth, args[0])
        except:
            # try DNS
            try:
                ip = socket.gethostbyaddr(args[0])[2][0]
            except:
                print "No droplet named "+args[0]+" and also not found in DNS"
                sys.exit(1)

    ip_yml_path = os.environ['HOME'] + "/.digitalocean.d/" + ip + ".yml"
    did_ssh = False
    try:
        info = load_yaml(ip_yml_path)
    except:
        print "Error reading "+ip_yml_path+" - proceeding with default ssh options (hopefully ~/.ssh/config is accurate for "+ip
        info = None

    if info is None:
        ssh([ip])
    else:
        ssh(['-i', info['key_path'], info['user']+'@'+ip])

elif command == "droplets" or command == "list":
    if len(args) == 0:
        pretty_print_json(get_droplets(auth))
    elif len(args) == 1:
        pretty_print_json(find_droplet_by_name(auth, args[0]))
    else:
        print "droplets requires zero args (list all droplets) or 1 arg (show droplet with that name)"
        sys.exit(1)

elif command == "droplet-ip":
    if len(args) != 1:
        print "droplet-ip requires 1 arg: name"
        sys.exit(1)
    print get_droplet_ip(auth, args[0])

elif command == "droplet" or command == "show" or command == "view" or command == "inspect":
    if len(args) != 1:
        print "droplet requires 1 arg: name"
        sys.exit(1)
    print pretty_print_json(find_droplet_by_name(auth, args[0]))

elif command == "create":
    if len(args) != 2:
        print "create requires exactly 2 args: machine-type name"
        sys.exit(1)

    mtype = args[0]
    name = args[1]
    machine = load_machine(mtype)

    # find size_id, image_id, and region_id
    machine['image_id'] = find_image_id(auth, machine['image_id'])
    machine['region_id'] = find_region_id(auth, machine['region_id'])
    machine['size_id'] = find_size_id(auth, machine['size_id'])

    # find ssh key ids, rebuild array
    key_ids = []
    for key_id in machine['ssh_key_ids']:
        key_ids.append(str(find_key_id(auth, key_id)))
    machine['ssh_key_ids'] = key_ids

    machine['name'] = name

    print "Creating droplet type=" + mtype + ", config=" + str(machine)+"\n...\n"
    response = requests.get(API_BASE+'/droplets/new', params=dict(machine.items() + auth.items()))
    print "Response from "+response.url+" was:\n"
    body = response.text
    print body + "\n"

    droplet = json.loads(body)
    if droplet['status'] != 'OK':
        print "Error creating droplet"
        sys.exit(1)

    id = droplet['droplet']['id']
    droplet = json.loads(find_droplet_by_id(auth, id))
    while droplet['droplet']['ip_address'] is None:
        print "No ip_address found for droplet "+str(id)+", asking again...\n"
        time.sleep(2)
        droplet = json.loads(find_droplet_by_id(auth, id))

    print "Droplet "+name+" (type="+mtype+") is now live: "+droplet['droplet']['ip_address']+"\n"

elif command == "destroy":
    if len(args) != 1:
        print "destroy requires 1 arg: name"
        sys.exit(1)
    name = args[0]
    id = find_droplet_id(auth, name)
    if id is None:
        print "No droplet found with name " + name
    destroy_params = []
    destroy_params['scrub_data'] = 'true'
    print requests.get(API_BASE+'/droplets/' + str(id) + '/destroy', params=dict(destroy_params.items() + auth.items()).text

elif command == "bootstrap":
    if len(args) != 3:
        print "bootstrap requires 3 args: name/ip user /path/to/key.pub"
        sys.exit(1)
    ip = args[0]
    user = args[1]
    key_path = args[2]
    execute_shell_internal([os.path.dirname(sys.argv[0])+"/do_bootstrap.sh", ip, user, key_path])

else:
    print "unknown command: " + command

