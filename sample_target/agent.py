"""Intentionally unsafe examples; the auditor only reads this file."""
import subprocess
import yaml

def run_agent(user_input):
    eval(user_input)
    exec(user_input)
    subprocess.run(user_input, shell=True)
    return yaml.load(user_input)
