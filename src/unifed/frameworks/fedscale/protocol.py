# import os
# import json
# import subprocess
# import tempfile
# import logging
# from typing import List

# import colink as CL

# from unifed.frameworks.fedscale.util import store_error, store_return, get_local_ip

# pop = CL.ProtocolOperator(__name__)
# UNIFED_TASK_DIR = "unifed:task"


# USE_FILE_LOGGING = True
# if USE_FILE_LOGGING:
#     logging.basicConfig(filename="temp.log",
#                         filemode='a',
#                         format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
#                         datefmt='%H:%M:%S',
#                         level=logging.DEBUG)


# def load_config_from_param_and_check(param: bytes):
#     unifed_config = json.loads(param.decode())
#     framework = unifed_config["framework"]
#     assert framework == "fedscale"
#     deployment = unifed_config["deployment"]
#     if deployment["mode"] != "colink":
#         raise ValueError("Deployment mode must be colink")
#     return unifed_config

# def convert_unifed_config_to_fedscale_config(unifed_config):  # note that for the target config, the "data" field is still missing
#     fedscale_config = {
#         "n_parties": len(unifed_config["deployment"]["participants"]) - 1, 
#          "verbose": 1,
#     }
#     if unifed_config['algorithm'] == 'fedavg':
#         fedscale_config["algorithm"] = "fed_avg"
#     else:
#         raise ValueError(f"Unknown algorithm {unifed_config['algorithm']}")
    

#     return fedscale_config


# def create_conf_file_content_from_fedscale_config(fedscale_config):
#     conf_file_content = ""
#     for key, value in fedscale_config.items():
#         conf_file_content += f"{key}={value}\n"
#     return conf_file_content


# def filter_log_from_fedscale_output(output):
#     filtered_output = ""
#     for line in output.split("\n"):
#         line_json = json.dumps({"fedscale": line})  # TODO: convert log here
#         if ".cpp" in line:
#             filtered_output += f"{line_json}\n"
#     return filtered_output


# @pop.handle("unifed.fedscale:server")
# @store_error(UNIFED_TASK_DIR)
# @store_return(UNIFED_TASK_DIR)
# def run_server(cl: CL.CoLink, param: bytes, participants: List[CL.Participant]):
#     logging.info(f"{cl.get_task_id()[:6]} - Server - Started")
#     print("running server start")
#     unifed_config = load_config_from_param_and_check(param)
#     fedscale_config = convert_unifed_config_to_fedscale_config(unifed_config)

#     temp_conf_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
#     temp_conf_file.write(create_conf_file_content_from_fedscale_config(fedscale_config))
#     temp_conf_file.close()

#     participant_id = [i for i, p in enumerate(participants) if p.user_id == cl.get_user_id()][0]
#     process = subprocess.Popen(
#         [
#             "unifed-fedscale",
#             "server",
#             temp_conf_file.name,
#         ],
#         stdout=subprocess.PIPE, 
#         stderr=subprocess.PIPE,
#     )

#     print("run_server process open")

#     # make sure the server is started first before sharing IP
#     server_ip = get_local_ip()
#     cl.send_variable("server_ip", server_ip, [p for p in participants if p.role == "client"])
#     # as soon as one client finishes, all clients should have finished
#     print(' setting fariable server ip')
#     first_client_return_code = cl.recv_variable("client_finished", [p for p in participants if p.role == "client"][0]).decode()
#     print(' run server client finished')
#     process.kill()
#     stdout, stderr = process.communicate()
#     print(' run server calculating output')
#     log = filter_log_from_fedscale_output(stdout.decode() + stderr.decode())
#     # TODO: store the model
#     cl.create_entry(f"{UNIFED_TASK_DIR}:{cl.get_task_id()}:log", log)
#     os.unlink(temp_conf_file.name)
#     return json.dumps({
#         "server_ip": server_ip,
#         "stdout": stdout.decode(),
#         "stderr": stderr.decode(),
#         "returncode": int(first_client_return_code),
#     })
    
    
# @pop.handle("unifed.fedscale:client")
# @store_error(UNIFED_TASK_DIR)
# @store_return(UNIFED_TASK_DIR)
# def run_client(cl: CL.CoLink, param: bytes, participants: List[CL.Participant]):
#     print('run client start')
#     logging.info(f"{cl.get_task_id()[:6]} - Client[(unknown)] - Started")
#     server_in_list = [p for p in participants if p.role == "server"]
#     assert len(server_in_list) == 1, f"There should be exactly one server, not {len(server_in_list)} servers ({server_in_list})."
#     p_server = server_in_list[0]
#     def get_client_id():
#         passed_server = 0
#         for i, p in enumerate(participants):
#             if p.role == "server":
#                 passed_server += 1
#             if p.user_id == cl.get_user_id():
#                 return i - passed_server
#     client_id = get_client_id()
#     print('run client client_id',client_id)
#     logging.info(f"{cl.get_task_id()[:6]} - Client[{client_id}] - Recognized")

#     unifed_config = load_config_from_param_and_check(param)
#     fedscale_config = convert_unifed_config_to_fedscale_config(unifed_config)
#     print('run client fedscale config:',fedscale_config)
#     fedscale_config["data"] = f"./data/{unifed_config['dataset']}_{client_id}.csv"
#     test_data_path = f"./data/{unifed_config['dataset']}"+"_test.csv"
#     if os.path.isfile(f"{test_data_path}"):
#         fedscale_config["test_data"] = test_data_path
#     server_ip = fedscale_config["ip_address"] = cl.recv_variable("server_ip", p_server).decode()

#     print('run_client_fedscale_config:',fedscale_config)

#     temp_conf_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
#     temp_conf_file.write(create_conf_file_content_from_fedscale_config(fedscale_config))
#     temp_conf_file.close()
#     process = subprocess.Popen(
#         [
#             "./bin/FedScale-distributed-party",
#             # takes 2 arg: config file path, client id
#             temp_conf_file.name,
#             str(client_id),
#         ],
#         stdout=subprocess.PIPE, 
#         stderr=subprocess.PIPE,
#     )
#     stdout, stderr = process.communicate()
#     returncode = process.returncode
#     logging.info(f"{cl.get_task_id()[:6]} - Client[{client_id}] - Subprocess finished with return code {returncode}")
#     # as soon as one client finishes, all clients should have finished
#     print('start running!')
#     if client_id == 0:
#         cl.send_variable("client_finished", returncode, server_in_list)
#     log = filter_log_from_fedscale_output(stdout.decode() + stderr.decode())
#     cl.create_entry(f"{UNIFED_TASK_DIR}:{cl.get_task_id()}:log", log)
#     os.unlink(temp_conf_file.name)
#     return json.dumps({
#         "server_ip": server_ip,
#         "stdout": stdout.decode(),
#         "stderr": stderr.decode(),
#         "returncode": returncode,
#     })


import os
import json
import sys
import subprocess
import tempfile
from typing import List
import time
import datetime
import yaml
import socket
import pickle

import colink as CL

from unifed.frameworks.example.util import store_error, store_return, GetTempFileName, get_local_ip

pop = CL.ProtocolOperator(__name__)
UNIFED_TASK_DIR = "unifed:task"

def load_config_from_param_and_check(param: bytes):
    unifed_config = json.loads(param.decode())
    framework = unifed_config["framework"]
    assert framework == "fedscale"
    deployment = unifed_config["deployment"]
    if deployment["mode"] != "colink":
        raise ValueError("Deployment mode must be colink")
    return unifed_config

def load_yaml_conf(yaml_file):
    with open(yaml_file) as fin:
        data = yaml.load(fin, Loader=yaml.FullLoader)
    return data

def config_to_FedScale_format(origin_json_conf):
    json_conf = dict()
    json_conf["framework"] = "FedScale"
    json_conf["dataset"] = origin_json_conf["dataset"]
    if origin_json_conf["algorithm"] == "fedavg":
        json_conf["algorithm"] = "fed_avg"
    json_conf["model"] = origin_json_conf["model"]
    json_conf["bench_param"] = {"mode": "local","device": "gpu"}
    json_conf["training_param"] = origin_json_conf["training"]
    json_conf["data_dir"] = "/home/haoyukim/data"
    return json_conf

def load_json_conf(json_file):
    with open(json_file) as fin:
        data = json.load(fin)
    return data

def process_cmd_server(json_conf, local=False):
    yaml_conf = {'ps_ip': 'localhost', 'ps_port': 29664, 'worker_ips': ['localhost:[2]'], 'exp_path': '~/colink-unifed-fedscale/FedScale/fedscale/cloud', 'executor_entry': 'execution/executor.py', 'aggregator_entry': 'aggregation/aggregator.py', 'auth': {'ssh_user': '', 'ssh_private_key': '~/.ssh/id_rsa'}, 'setup_commands': ['source $HOME/anaconda3/bin/activate fedscale'], 'job_conf': [{'job_name': 'BASE'}, {'seed': 1}, {'log_path': './benchmark'}, {'task': 'simple'}, {'num_participants': 2}, {'data_set': 'breast_horizontal'}, {'data_dir': '../data/csv_data/breast_horizontal'}, {'model': 'logistic_regression'}, {'gradient_policy': 'fed-avg'}, {'eval_interval': 5}, {'rounds': 6}, {'filter_less': 1}, {'num_loaders': 2}, {'local_steps': 5}, {'inner_step': 1}, {'learning_rate': 0.01}, {'batch_size': 32}, {'test_bsz': 32}, {'use_cuda': False}]}

    print("process_cmd_server start")
    use_container = "default"

    ps_ip = yaml_conf['ps_ip']
    worker_ips, total_gpus = [], []
    cmd_script_list = []
    max_process = min(4, json_conf["training_param"]["client_per_round"])

    executor_configs = "=".join(yaml_conf['worker_ips']).split(':')[0] + f':[{max_process}]'
    if 'worker_ips' in yaml_conf:
        for ip_gpu in yaml_conf['worker_ips']:
            ip, gpu_list = ip_gpu.strip().split(':')
            worker_ips.append(ip)
            # total_gpus.append(eval(gpu_list))
            total_gpus.append([max_process])

    time_stamp = datetime.datetime.fromtimestamp(
        time.time()).strftime('%m%d_%H%M%S')
    running_vms = set()
    job_name = 'fedscale_job'
    log_path = './logs'
    submit_user = f"{yaml_conf['auth']['ssh_user']}@" if len(yaml_conf['auth']['ssh_user']) else ""

    job_conf = {'time_stamp': time_stamp,
                'ps_ip': ps_ip,
                }

    for conf in yaml_conf['job_conf']:
        job_conf.update(conf)

    conf_script = ''
    setup_cmd = ''
    if yaml_conf['setup_commands'] is not None:
        setup_cmd += (yaml_conf['setup_commands'][0] + ' && ')
        for item in yaml_conf['setup_commands'][1:]:
            setup_cmd += (item + ' && ')

    cmd_sufix = f" "


    for conf_name in job_conf:
        if conf_name == "job_name":
            job_conf[conf_name] = json_conf["dataset"] + '+' + json_conf["model"]
        elif conf_name == "task":
            if json_conf['dataset'] == 'femnist':
                job_conf[conf_name] = 'cv'
            else:
                job_conf[conf_name] = "simple" # TO-DO ?
        elif conf_name == "num_participants":
            job_conf[conf_name] = json_conf["training_param"]["client_per_round"]
        elif conf_name == "data_set":
            if json_conf['dataset'] == 'femnist':
                job_conf[conf_name] = 'femnist2'
            else:
                job_conf[conf_name] = json_conf["dataset"]
        elif conf_name == "data_dir":
            if json_conf['dataset'] == 'femnist':
                job_conf[conf_name] = json_conf["data_dir"] + "/" + json_conf["dataset"]
            else:
                job_conf[conf_name] = json_conf["data_dir"] + "/csv_data/" + json_conf["dataset"]
        elif conf_name == "model":
            job_conf[conf_name] = json_conf["model"]
        elif conf_name == "gradient_policy":
            job_conf[conf_name] = json_conf["algorithm"]
        elif conf_name == "eval_interval":
            job_conf[conf_name] = 1 # json_conf["training_param"]["epochs"] 
        elif conf_name == "rounds":
            job_conf[conf_name] = json_conf["training_param"]["epochs"] + 1
        elif conf_name == "inner_step":
            job_conf[conf_name] = json_conf["training_param"]["inner_step"]
        elif conf_name == "learning_rate":
            job_conf[conf_name] = json_conf["training_param"]["learning_rate"]
        elif conf_name == "batch_size":
            job_conf[conf_name] = json_conf["training_param"]["batch_size"]
        elif conf_name == "use_cuda":
            job_conf[conf_name] = (json_conf["bench_param"]["device"] == "gpu")

        conf_script = conf_script + f' --{conf_name}={job_conf[conf_name]}'
        if conf_name == "job_name":
            job_name = job_conf[conf_name]
        if conf_name == "log_path":
            log_path = os.path.join(
                job_conf[conf_name], 'log', job_name, time_stamp)

    if json_conf['dataset'] == 'femnist':
        conf_script = conf_script + ' --temp_tag=simple_femnist'

    print(conf_script)

    total_gpu_processes = sum([sum(x) for x in total_gpus])


    # =========== Submit job to parameter server ============
    running_vms.add(ps_ip)
    print(f"Starting aggregator on {ps_ip}...")
    ps_cmd = f" python {yaml_conf['exp_path']}/{yaml_conf['aggregator_entry']} {conf_script} --this_rank=0 --num_executors={total_gpu_processes} --executor_configs={executor_configs} "

    with open(f"{job_name}_logging", 'wb') as fout:
        pass

            
    return time_stamp, ps_cmd , submit_user, ps_ip, setup_cmd

def process_cmd_client(participant_id, json_conf, time_stamp, temp_output_filename, temp_log_filename, local=False):
    time.sleep(10)
    ps_name = f"fedscale-aggr-{time_stamp}"

    yaml_conf = {'ps_ip': 'localhost', 'ps_port': 29664, 'worker_ips': ['localhost:[2]'], 'exp_path': '~/colink-unifed-fedscale/FedScale/fedscale/cloud', 'executor_entry': 'execution/executor.py', 'aggregator_entry': 'aggregation/aggregator.py', 'auth': {'ssh_user': '', 'ssh_private_key': '~/.ssh/id_rsa'}, 'setup_commands': ['source $HOME/anaconda3/bin/activate fedscale'], 'job_conf': [{'job_name': 'BASE'}, {'seed': 1}, {'log_path': './benchmark'}, {'task': 'simple'}, {'num_participants': 2}, {'data_set': 'breast_horizontal'}, {'data_dir': '../data/csv_data/breast_horizontal'}, {'model': 'logistic_regression'}, {'gradient_policy': 'fed-avg'}, {'eval_interval': 5}, {'rounds': 6}, {'filter_less': 1}, {'num_loaders': 2}, {'local_steps': 5}, {'inner_step': 1}, {'learning_rate': 0.01}, {'batch_size': 32}, {'test_bsz': 32}, {'use_cuda': False}]}

    if 'use_container' in yaml_conf:
        if yaml_conf['use_container'] == "docker":
            use_container = "docker"
            ports = yaml_conf['ports']
        else:
            print(f'Error: unknown use_container:{yaml_conf["use_container"]}, the supported options are ["docker", "k8s"].')
            exit(1)
    else:
        use_container = "default"

    ps_ip = yaml_conf['ps_ip']
    worker_ips, total_gpus = [], []
    max_process = min(4, json_conf["training_param"]["client_per_round"])

    executor_configs = "=".join(yaml_conf['worker_ips']).split(':')[0] + f':[{max_process}]'
    if 'worker_ips' in yaml_conf:
        for ip_gpu in yaml_conf['worker_ips']:
            ip, gpu_list = ip_gpu.strip().split(':')
            worker_ips.append(ip)
            # total_gpus.append(eval(gpu_list))
            total_gpus.append([max_process])

    running_vms = set()
    job_name = 'fedscale_job'
    submit_user = f"{yaml_conf['auth']['ssh_user']}@" if len(yaml_conf['auth']['ssh_user']) else ""

    job_conf = {'time_stamp': time_stamp,
                'ps_ip': ps_ip,
                }

    for conf in yaml_conf['job_conf']:
        job_conf.update(conf)

    conf_script = ''
    setup_cmd = ''
    if yaml_conf['setup_commands'] is not None:
        setup_cmd += (yaml_conf['setup_commands'][0] + ' && ')
        for item in yaml_conf['setup_commands'][1:]:
            setup_cmd += (item + ' && ')

    cmd_sufix = f" "

    for conf_name in job_conf:
        if conf_name == "job_name":
            job_conf[conf_name] = json_conf["dataset"] + '+' + json_conf["model"]
        elif conf_name == "task":
            if json_conf['dataset'] == 'femnist':
                job_conf[conf_name] = 'cv'
            else:
                job_conf[conf_name] = "simple" # TO-DO ?
        elif conf_name == "num_participants":
            job_conf[conf_name] = json_conf["training_param"]["client_per_round"]
        elif conf_name == "data_set":
            if json_conf['dataset'] == 'femnist':
                job_conf[conf_name] = 'femnist2'
            else:
                job_conf[conf_name] = json_conf["dataset"]
        elif conf_name == "data_dir":
            if json_conf['dataset'] == 'femnist':
                job_conf[conf_name] = json_conf["data_dir"] + "/" + json_conf["dataset"]
            else:
                job_conf[conf_name] = json_conf["data_dir"] + "/csv_data/" + json_conf["dataset"]
        elif conf_name == "model":
            job_conf[conf_name] = json_conf["model"]
        elif conf_name == "gradient_policy":
            job_conf[conf_name] = json_conf["algorithm"]
        elif conf_name == "eval_interval":
            job_conf[conf_name] = 1 # json_conf["training_param"]["epochs"] 
        elif conf_name == "rounds":
            job_conf[conf_name] = json_conf["training_param"]["epochs"] + 1
        elif conf_name == "inner_step":
            job_conf[conf_name] = json_conf["training_param"]["inner_step"]
        elif conf_name == "learning_rate":
            job_conf[conf_name] = json_conf["training_param"]["learning_rate"]
        elif conf_name == "batch_size":
            job_conf[conf_name] = json_conf["training_param"]["batch_size"]
        elif conf_name == "use_cuda":
            job_conf[conf_name] = (json_conf["bench_param"]["device"] == "gpu")

        conf_script = conf_script + f' --{conf_name}={job_conf[conf_name]}'
        if conf_name == "job_name":
            job_name = job_conf[conf_name]
        if conf_name == "log_path":
            log_path = os.path.join(
                job_conf[conf_name], 'log', job_name, time_stamp)

    if json_conf['dataset'] == 'femnist':
        conf_script = conf_script + ' --temp_tag=simple_femnist'

    print(conf_script)

    total_gpu_processes = sum([sum(x) for x in total_gpus])

    # error checking
    if use_container == "docker" and total_gpu_processes + 1 != len(ports):
        print(f'Error: there are {total_gpu_processes + 1} processes but {len(ports)} ports mapped, please check your config file')
        exit(1)

    # =========== Submit job to each worker ============
    rank_id = 1
    for worker, gpu in zip(worker_ips, total_gpus):
        running_vms.add(worker)

        if use_container == "default":
            print(f"Starting workers on {worker} ...")

        for cuda_id in range(len(gpu)):
            for _ in range(gpu[cuda_id]):
                worker_cmd = f" python {yaml_conf['exp_path']}/{yaml_conf['executor_entry']} {conf_script} --this_rank={rank_id} --num_executors={total_gpu_processes} "
                if job_conf['use_cuda'] == True:
                    worker_cmd += f" --cuda_device=cuda:{cuda_id}"

                time.sleep(2)
                if rank_id == participant_id:
                    print(f"submitted: rank_id:{rank_id} worker_cmd:{worker_cmd}")
                    with open(temp_output_filename, "wb") as fout:
                        if local:
                            process = subprocess.Popen(f'{worker_cmd}',
                                                shell=True, stdout=fout, stderr=fout)
                        else:
                            process = subprocess.Popen(f'ssh {submit_user}{worker} "{setup_cmd} {worker_cmd}"',
                                shell=True, stdout=fout, stderr=fout)
                            stdout,stderr = process.communicate()
                            returncode = process.returncode
                rank_id += 1


    print(f"Submitted job!")

    return stdout,stderr,returncode


@pop.handle("unifed.fedscale:server")
@store_error(UNIFED_TASK_DIR)
@store_return(UNIFED_TASK_DIR)
def run_server(cl: CL.CoLink, param: bytes, participants: List[CL.Participant]):
    print("start run server")
    unifed_config = load_config_from_param_and_check(param)
    Config = config_to_FedScale_format(unifed_config)
    print("Config",Config)
    # for certain frameworks, clients need to learn the ip of the server
    # in that case, we get the ip of the current machine and send it to the clients
    server_ip = get_local_ip()
    cl.send_variable("server_ip", server_ip, [p for p in participants if p.role == "client"])
    # run external program
    participant_id = [i for i, p in enumerate(participants) if p.user_id == cl.get_user_id()][0]
    
    with GetTempFileName() as temp_log_filename, \
        GetTempFileName() as temp_output_filename:
        # note that here, you don't have to create temp files to receive output and log
        # you can also expect the target process to generate files and then read them


        time_stamp, ps_cmd, submit_user, ps_ip, setup_cmd = process_cmd_server(Config)

        cl.send_variable("time_stamp", json.dumps(time_stamp), [p for p in participants if p.role == "client"])

        # process = subprocess.Popen(f'{ps_cmd}', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process = subprocess.Popen(f'ssh {submit_user}{ps_ip} "{setup_cmd} {ps_cmd}"',shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = process.communicate()
        returncode = process.returncode

        with open(temp_output_filename, "rb") as f:
            output = f.read()
        cl.create_entry(f"{UNIFED_TASK_DIR}:{cl.get_task_id()}:output", output)
        with open(temp_log_filename, "rb") as f:
            log = f.read()
        cl.create_entry(f"{UNIFED_TASK_DIR}:{cl.get_task_id()}:log", log)
        return json.dumps({
            "server_ip": server_ip,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": returncode,
        })


@pop.handle("unifed.fedscale:client")
@store_error(UNIFED_TASK_DIR)
@store_return(UNIFED_TASK_DIR)
def run_client(cl: CL.CoLink, param: bytes, participants: List[CL.Participant]):
    print("start run client")
    unifed_config = load_config_from_param_and_check(param)
    Config = config_to_FedScale_format(unifed_config)
    # get the ip of the server
    server_in_list = [p for p in participants if p.role == "server"]
    assert len(server_in_list) == 1
    p_server = server_in_list[0]
    server_ip = cl.recv_variable("server_ip", p_server).decode()
    # run external program
    participant_id = [i for i, p in enumerate(participants) if p.user_id == cl.get_user_id()][0]
    
    
    time_stamp = cl.recv_variable("time_stamp", p_server).decode()
    print(f"time_stamp:{time_stamp}")
    print(f"participant_id:{participant_id}")
    
    with GetTempFileName() as temp_log_filename, \
        GetTempFileName() as temp_output_filename:
        # note that here, you don't have to create temp files to receive output and log
        # you can also expect the target process to generate files and then read them

        stdout,stderr,returncode = process_cmd_client(participant_id, Config, time_stamp, temp_output_filename, temp_log_filename)

        with open(temp_output_filename, "rb") as f:
            output = f.read()
        cl.create_entry(f"{UNIFED_TASK_DIR}:{cl.get_task_id()}:output", output)
        with open(temp_log_filename, "rb") as f:
            log = f.read()
        cl.create_entry(f"{UNIFED_TASK_DIR}:{cl.get_task_id()}:log", log)
        return json.dumps({
            "server_ip": server_ip,
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "returncode": returncode,
        })