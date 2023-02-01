"""SSH into equipment and gather serial number"""
import getpass
import os
import sys
import re
import csv
from getpass import getpass
from netmiko import ConnectHandler
from netmiko.ssh_exception import  NetMikoTimeoutException, AuthenticationException
from paramiko.ssh_exception import SSHException


def check_file(filename):
    """Verifying that an inventory file exists!"""
    exists1 = os.path.isfile(filename)
    if not exists1:
        print("Inventory file not found!")
        sys.exit()


def load_file(filename):
    """Inputs each line with out a comment into an array called hosts"""
    hosts = []
    with open(filename) as fh:
        for each_line in fh:
            if "#" not in each_line:
                hosts.append(each_line.strip("\n"))
    return hosts


def connect_and_gather(device_param, ip_address):
    """SSH into device to gather serial and part number"""

    net_connect = ConnectHandler(**device_param)

    # Prints the IP Address its connecting to
    hostname = net_connect.find_prompt()[:-1]
    print(
        f"Gathering information from switch: {ip_address} = {hostname}"
    )

    # Logs into the networking device
    show_version_result = net_connect.send_command(
        "show ver | in System [Ss]erial [Nn]umber|Model [Nn]umber"
    )
    show_version_result = show_version_result.split("\n")
    show_version_router_result = net_connect.send_command("show ver | in \*1")
    show_license_router_result = net_connect.send_command("show license udi | in \*")

    regex_p0 = re.compile(r".+\s:\s(?P<value>.+)")
    counter = 2
    serial_number = []
    pid = []
    for line in show_version_result:
        mod = counter % 2
        if mod == 0:
            match_found = regex_p0.match(line)
            print(f"even line = {line}")

            # Return serial number if the device is a switch
            if match_found:
                value = match_found.groupdict()["value"]
                pid.append(value.strip("\n"))

            # Return serianel and part number if device is a legacy Router
            elif "*1" in show_version_router_result:
                show_version_router_result = (
                    show_version_router_result.strip("\n").lstrip("*1\t ").rstrip(" ")
                )
                show_version_router_result = show_version_router_result.split(" ")
                print(f"Legacy Router: {show_version_router_result}")
                pid.append(show_version_router_result[0])
                serial_number.append(show_version_router_result[-1])

            # Return serianel and part number if device is a new Router
            elif "*" in show_license_router_result:
                show_license_router_result = (
                    show_license_router_result.strip("\n").lstrip("*\t ").rstrip(" ")
                )
                show_license_router_result = show_license_router_result.split(" ")
                show_license_router_result = show_license_router_result[-1].split(":")
                print(f"New Router: {show_license_router_result}")
                pid.append(show_license_router_result[0])
                serial_number.append(show_license_router_result[-1])

        # Return part number for switch
        else:
            match_found = regex_p0.match(line)
            print(f"odd line = {line}")
            if match_found:
                value = match_found.groupdict()["value"]
                serial_number.append(value.strip("\n"))
            else:
                print("no odd match")
        counter += 1
    print()
    for serial_number_, pid_ in zip(serial_number, pid):
        write_to_file([serial_number_, pid_, hostname])

    net_connect.disconnect()


def write_to_file(input):
    """Write information to CSV file"""
    with open("device_inventory.csv", "a") as file_handler:
        writer = csv.writer(file_handler)
        writer.writerow(input)


if __name__ == "__main__":
    FILENAME = "inventory.txt"
    check_file(FILENAME)
    hosts = load_file(FILENAME)
    username = input("Username:")
    password = getpass()

    # Write header
    write_to_file(["Serial Number", "PID", "Hostname"])

    for host in hosts:

        device_parameters = {
            "device_type": "cisco_ios",
            "ip": host,
            "username": username,
            "password": password,
        }

        try:
            connect_and_gather(device_parameters, host)
        except AuthenticationException:
            print('Authentication Failure: ' + host)
            sys.exit()
        except NetMikoTimeoutException:
            print('Timeout to device: ' + host)
            continue
        except SSHException:
            print('SSH might not be enabled: ' + host)
            continue
        except EOFError:
            print('End of attempting device: ' +  host)
            continue
        except Exception as unknown_error:
            write_to_file([unknown_error, "Error", host])
            continue
