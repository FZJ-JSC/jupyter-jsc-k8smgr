#!/bin/bash
echo "Hello World from my Script"

echo "Replace project_kernel: <hook_project_kernel>"
echo "Replace user_options system: <system>"
echo "Replace env JUPYTERHUB_USER_ID: <JUPYTERHUB_USER_ID>"

if [[ <hook_project_kernel> -eq 1 ]]; then
    echo "Use project kernel"
fi

if [[ <hook_multiple_keys> -eq 1 ]]; then
    echo "Use multiple_keys hook"
fi
